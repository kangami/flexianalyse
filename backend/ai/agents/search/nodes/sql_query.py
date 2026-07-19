# backend/ai/agents/search/nodes/sql_query.py
"""
Live SQL Query Node — Text-to-SQL
=================================
Unlike the vector / FTS / KG retrieval (which searches *ingested* document
chunks), this node queries the organization's connected SQL database **in real
time** when the user asks a data question (e.g. "how many active clients do we
have?", "total revenue per month in 2025").

Flow:
  1. Skip unless `needs_database` is set and the "sql" connector is allowed.
  2. Resolve the org's active SQL connector and decrypt its database URL.
  3. Introspect the schema through the SQL MCP server.
  4. Generate a single read-only SELECT from natural language (LLM).
  5. Defensively validate the SQL, then execute it via the MCP server.
  6. Store rows on the state so `assemble_context` can ground the answer.

Note: the MCP client used elsewhere (`services.mcp_http_client`) is async, but
LangGraph nodes here run synchronously inside Flask's async view (an already
running event loop), so we talk to the SQL MCP server over **synchronous** HTTP
to avoid nested-event-loop errors.
"""
import os
import re
import json
import time
import logging

import httpx

from ai.agents.search.state import SearchState
from ai.observability import make_openai_client

logger = logging.getLogger(__name__)
_client = make_openai_client()

# Must match services.mcp_http_client.MCP_SERVERS["sql"] / docker-compose port.
# Tolerate a scheme-less host:port (Render's `fromService: hostport`).
SQL_MCP_URL = os.getenv("SQL_MCP_URL", "http://localhost:3001").strip()
if SQL_MCP_URL and "://" not in SQL_MCP_URL:
    SQL_MCP_URL = f"http://{SQL_MCP_URL}"

MAX_TABLES_IN_PROMPT = 30    # include enough tables so JOIN targets aren't cut off
MAX_RESULT_ROWS      = 50    # cap rows pulled into the answer context
SQL_GEN_MODEL        = "gpt-5-mini"

# In-process schema cache (per database URL) — avoids 1+N introspection HTTP
# calls on every DB query. Short TTL so schema changes are picked up.
_SCHEMA_CACHE: dict[str, tuple[float, str]] = {}
_SCHEMA_TTL = 300  # seconds


def sql_query(state: SearchState) -> SearchState:
    """Generate and run a live SQL query when the question targets the database."""
    # Idempotent on the retry loop — don't re-run if we already have a result.
    if state.get("sql_rows") or state.get("sql_error"):
        return state

    allowed = set(state.get("allowed_connectors") or [])
    if "sql" not in allowed:
        logger.info("SQL node skipped — 'sql' connector not allowed")
        return state

    org_id = state["org_id"]
    query = state["query"]

    # Robust routing — the single-LLM `needs_database` flag is unreliable, so we
    # ALSO run the SQL path when the query names a known table or clearly asks
    # for data. Naming a known table is the strongest signal.
    known_tables = _known_sql_tables(org_id)
    if not (
        state.get("needs_database")
        or _mentions_known_table(query, known_tables)
        or _looks_like_db_query(query)
    ):
        return state

    try:
        database_url = _get_database_url(org_id)
        if not database_url:
            logger.info("SQL node skipped — no active SQL connector for org %s", org_id)
            return state

        schema = _fetch_schema(database_url)
        if not schema:
            return {**state, "sql_error": "Could not read the database schema"}

        sql = _generate_sql(state["query"], schema)
        if not sql:
            # Not answerable from the DB schema → silently fall back to document
            # search (no error note that would pollute a plain document answer).
            return state

        if not _is_safe_select(sql):
            logger.warning("SQL node rejected an unsafe statement: %s", sql)
            return {**state, "generated_sql": sql,
                    "sql_error": "Generated query was not a safe read-only SELECT"}

        result = _call_sql_tool(
            "query_database",
            {"sql_query": sql, "limit": MAX_RESULT_ROWS},
            database_url,
        )
        if result.get("status") != "success":
            return {**state, "generated_sql": sql,
                    "sql_error": result.get("message", "Query execution failed")}

        rows = result.get("rows", [])
        logger.info("SQL node: %d rows returned for org %s", len(rows), org_id)
        return {
            **state,
            "generated_sql": sql,
            "sql_columns": result.get("columns", []),
            "sql_rows": rows,
        }

    except Exception as e:
        logger.error("SQL node failed: %s", e, exc_info=True)
        return {**state, "sql_error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Routing helpers
# ─────────────────────────────────────────────────────────────────────────────

# Kept deliberately narrow (strong "structured data" signals) so plain document
# questions don't needlessly trigger the SQL path. A known-table mention or the
# LLM `needs_database` flag covers the rest.
_DB_KEYWORDS = (
    "how many", "how much", "number of", "count of", "rows", "records",
    "total of", "sum of", "average of", "group by", "top ",
)


def _known_sql_tables(org_id: str) -> list[str]:
    """Table names known locally for this org's SQL connector(s) — a fast local
    DB lookup (no network) used to detect table mentions in the query."""
    from models.resource import Resource
    try:
        rows = Resource.query.filter(
            Resource.organization_id == org_id,
            Resource.type.in_(("sql", "sql_table")),
            Resource.deleted_at.is_(None),
        ).all()
        return [r.title for r in rows if r.title]
    except Exception as e:
        logger.warning("Could not load known SQL tables for org %s: %s", org_id, e)
        return []


def _mentions_known_table(query: str, tables: list[str]) -> bool:
    """True if the query contains a known table name as a whole word."""
    if not tables:
        return False
    words = set(re.findall(r"\w+", query.lower()))
    return any(t and t.lower() in words for t in tables)


def _looks_like_db_query(query: str) -> bool:
    """Heuristic: does the query read like a request for structured data?"""
    q = query.lower()
    return any(kw in q for kw in _DB_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_database_url(org_id: str) -> str | None:
    """Resolve and decrypt the database URL of the org's active SQL connector."""
    from models.connector import Connector, ConnectorCredentials
    from services.encryption_service import EncryptionService

    connector = Connector.query.filter_by(
        organization_id=org_id,
        type="sql",
        status="active",
        deleted_at=None,
    ).first()
    if not connector:
        return None

    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None,
    ).first()
    if not creds or not creds.encrypted_token:
        return None

    try:
        return EncryptionService().decrypt(creds.encrypted_token)
    except Exception as e:
        logger.error("Failed to decrypt SQL credentials for org %s: %s", org_id, e)
        return None


def _call_sql_tool(tool_name: str, params: dict, database_url: str, timeout: int = 30) -> dict:
    """Synchronous call to the SQL MCP server's /execute endpoint."""
    body = {"tool_name": tool_name, "params": params or {}, "database_url": database_url}
    resp = httpx.post(f"{SQL_MCP_URL}/execute", json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _fetch_schema(database_url: str) -> str:
    """Introspect tables + columns (+ FKs) and render a compact schema string.
    Cached per database URL for `_SCHEMA_TTL` seconds."""
    cached = _SCHEMA_CACHE.get(database_url)
    if cached and (time.time() - cached[0]) < _SCHEMA_TTL:
        return cached[1]

    tables_res = _call_sql_tool("show_tables", {}, database_url)
    tables = (tables_res.get("tables") or [])[:MAX_TABLES_IN_PROMPT]
    if not tables:
        return ""

    lines: list[str] = []
    for table in tables:
        try:
            schema_res = _call_sql_tool("show_table_schema", {"table_name": table}, database_url)
            sch = schema_res.get("schema", {})
            columns = sch.get("columns", [])
            col_str = ", ".join(f'{c["name"]} {c["type"]}' for c in columns)
            line = f"{table}({col_str})"

            # Surface foreign keys so the generator can JOIN related tables.
            fks = sch.get("foreign_keys", [])
            if fks:
                fk_str = "; ".join(
                    f"{','.join(fk.get('columns', []))} -> "
                    f"{fk.get('referred_table')}({','.join(fk.get('referred_columns', []))})"
                    for fk in fks if fk.get("referred_table")
                )
                if fk_str:
                    line += f"  [FK: {fk_str}]"
            lines.append(line)
        except Exception as e:
            logger.warning("Schema read failed for table %s: %s", table, e)
            lines.append(f"{table}(...)")

    schema_str = "\n".join(lines)
    _SCHEMA_CACHE[database_url] = (time.time(), schema_str)
    return schema_str


def _generate_sql(question: str, schema: str) -> str:
    """Translate a natural-language question into a single read-only SELECT."""
    prompt = f"""Database schema. Each line is `table(column type, ...)` and may
end with `[FK: col -> other_table(col)]` describing foreign-key relationships:
{schema}

User question: {question}

Write a single read-only SQL SELECT query (PostgreSQL dialect) that answers it.
Rules:
- SELECT statements ONLY — never INSERT/UPDATE/DELETE/DROP/ALTER/etc.
- Use only tables and columns that appear in the schema above.
- When the question spans related tables, JOIN them using the [FK: ...]
  relationships shown in the schema.
- Do not append a trailing semicolon.
- Do not add a LIMIT clause; a row limit is applied automatically.
- If the question cannot be answered from this schema, return an empty string.

Return JSON exactly as: {{"sql": "..."}}"""

    response = _client.chat.completions.create(
        model=SQL_GEN_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert text-to-SQL engine. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        # Reasoning model: minimal effort so the budget yields output, not empty
        # content. extra_body keeps this independent of the SDK version.
        max_completion_tokens=800,
        extra_body={"reasoning_effort": "minimal"},
    )

    data = json.loads(response.choices[0].message.content)
    return (data.get("sql") or "").strip()


_FORBIDDEN_KEYWORDS = (
    "insert ", "update ", "delete ", "drop ", "alter ", "truncate ",
    "create ", "grant ", "revoke ", "merge ", "call ", "exec ",
)


def _is_safe_select(sql: str) -> bool:
    """Defense-in-depth: only allow a single read-only SELECT statement.

    The MCP server also enforces SELECT-only, but we validate here too so an
    unsafe generation never reaches the wire.
    """
    s = sql.strip().lower()
    if not s.startswith("select"):
        return False
    # Disallow statement chaining (e.g. "select 1; drop table x").
    if ";" in s.rstrip(";"):
        return False
    return not any(kw in s for kw in _FORBIDDEN_KEYWORDS)
