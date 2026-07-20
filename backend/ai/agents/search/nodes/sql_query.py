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
from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

# Must match services.mcp_http_client.MCP_SERVERS["sql"] / docker-compose port.
# Tolerate a scheme-less host:port (Render's `fromService: hostport`).
SQL_MCP_URL = os.getenv("SQL_MCP_URL", "http://localhost:3001").strip()
if SQL_MCP_URL and "://" not in SQL_MCP_URL:
    SQL_MCP_URL = f"http://{SQL_MCP_URL}"

MAX_TABLES_IN_PROMPT = 30    # include enough tables so JOIN targets aren't cut off
MAX_RESULT_ROWS      = 50    # cap rows pulled into the answer context
# gpt-4o (not -mini) is markedly more reliable at multi-table joins, esp. joining
# through association tables — worth the cost for correctness. Override via env.
SQL_GEN_MODEL        = os.getenv("SQL_GEN_MODEL", "gpt-4o")

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
        connector = _resolve_sql_connector(org_id, state.get("scope_connector_id"))
        if not connector:
            logger.info("SQL node skipped — no active SQL connector for org %s", org_id)
            return state
        database_url = _decrypt_connector_url(connector)
        if not database_url:
            logger.info("SQL node skipped — no usable credentials for connector %s", connector.id)
            return state

        limits = _org_plan_limits(org_id)

        schema = _fetch_schema_smart(connector, query, database_url, limits)
        if not schema:
            return {**state, "sql_error": "Could not read the database schema"}

        sql = _generate_sql(state["query"], schema, limits["sql_model"])
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
            {"sql_query": sql, "limit": limits.get("max_rows", MAX_RESULT_ROWS)},
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

def _org_plan_limits(org_id: str) -> dict:
    """Plan-tier limits (catalog/retrieval/model/rows) for the org — see config/plans."""
    from models.organization import Organization
    from config.plans import plan_limits
    from uuid import UUID
    try:
        org = Organization.query.get(UUID(org_id)) if org_id else None
        return plan_limits(org.plan if org else None)
    except Exception:
        return plan_limits(None)


def _resolve_sql_connector(org_id: str, connector_id: str | None = None):
    """The org's active SQL connector row (the exact one when `connector_id` is
    given via the search-perimeter selector, else the first). None if none."""
    from models.connector import Connector
    from uuid import UUID

    q = Connector.query.filter_by(
        organization_id=org_id,
        type="sql",
        status="active",
        deleted_at=None,
    )
    if connector_id:
        try:
            q = q.filter(Connector.id == UUID(connector_id))
        except (ValueError, TypeError):
            return None
    return q.first()


def _decrypt_connector_url(connector) -> str | None:
    """Decrypt a connector's stored database URL. None if missing/undecryptable."""
    from models.connector import ConnectorCredentials
    from services.encryption_service import EncryptionService

    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None,
    ).first()
    if not creds or not creds.encrypted_token:
        return None
    try:
        return EncryptionService().decrypt(creds.encrypted_token)
    except Exception as e:
        logger.error("Failed to decrypt SQL credentials for connector %s: %s", connector.id, e)
        return None


def _get_database_url(org_id: str, connector_id: str | None = None) -> str | None:
    """Resolve and decrypt the database URL of the org's SQL connector.

    When `connector_id` is given (the search-perimeter selector), use that exact
    connector — but only if it belongs to the org and is an active SQL connector.
    Otherwise fall back to the org's first active SQL connector.
    """
    connector = _resolve_sql_connector(org_id, connector_id)
    if not connector:
        return None
    return _decrypt_connector_url(connector)


def _call_sql_tool(tool_name: str, params: dict, database_url: str, timeout: int = 30) -> dict:
    """Synchronous call to the SQL MCP server's /execute endpoint."""
    body = {"tool_name": tool_name, "params": params or {}, "database_url": database_url}
    resp = httpx.post(f"{SQL_MCP_URL}/execute", json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# Schema introspection is far slower than a data query on a large database
# (dozens of catalog queries), so it gets its own, more generous HTTP timeout.
SCHEMA_FETCH_TIMEOUT = int(os.getenv("SQL_SCHEMA_TIMEOUT", "90"))


def fetch_tables_meta(database_url: str, limit: int = MAX_TABLES_IN_PROMPT) -> list[dict]:
    """Structured schema: [{name, columns:[{name,type,pk}], foreign_keys:[...]}].

    Uses the batched `show_full_schema` (one round-trip, bulk reflection); `limit`
    caps how many tables the server introspects so a large database (hundreds of
    tables) doesn't time out — the callers only render the first N anyway. Falls
    back to the old per-table calls if the MCP server predates that tool, so a
    rolling deploy keeps working. Shared by the Text-to-SQL node and dbAnalyse.
    """
    res = _call_sql_tool(
        "show_full_schema", {"limit": limit}, database_url, timeout=SCHEMA_FETCH_TIMEOUT
    )
    if res.get("status") == "success" and isinstance(res.get("tables"), list):
        return [
            {
                "name": t.get("table"),
                "columns": [
                    {"name": c["name"], "type": str(c.get("type", "")), "pk": bool(c.get("is_primary_key"))}
                    for c in t.get("columns", [])
                ],
                "foreign_keys": t.get("foreign_keys", []),
            }
            for t in res["tables"]
        ]

    # Fallback — per-table introspection (older MCP server without show_full_schema).
    names = (_call_sql_tool("show_tables", {}, database_url).get("tables") or [])[:limit]
    out = []
    for name in names:
        try:
            sch = _call_sql_tool("show_table_schema", {"table_name": name}, database_url).get("schema", {})
            out.append({
                "name": name,
                "columns": [
                    {"name": c["name"], "type": str(c.get("type", "")), "pk": bool(c.get("is_primary_key"))}
                    for c in sch.get("columns", [])
                ],
                "foreign_keys": sch.get("foreign_keys", []),
            })
        except Exception as e:
            logger.warning("Schema read failed for table %s: %s", name, e)
    return out


def _fetch_schema(database_url: str) -> str:
    """Render a compact schema string for the SQL generator. Cached per URL."""
    cached = _SCHEMA_CACHE.get(database_url)
    if cached and (time.time() - cached[0]) < _SCHEMA_TTL:
        return cached[1]

    tables = fetch_tables_meta(database_url)[:MAX_TABLES_IN_PROMPT]
    if not tables:
        return ""

    lines: list[str] = []
    for t in tables:
        col_str = ", ".join(f'{c["name"]} {c["type"]}' for c in t["columns"])
        line = f'{t["name"]}({col_str})'
        fks = t.get("foreign_keys", [])
        if fks:
            fk_str = "; ".join(
                f"{','.join(fk.get('columns', []))} -> "
                f"{fk.get('referred_table')}({','.join(fk.get('referred_columns', []))})"
                for fk in fks if fk.get("referred_table")
            )
            if fk_str:
                line += f"  [FK: {fk_str}]"
        lines.append(line)

    schema_str = "\n".join(lines)
    _SCHEMA_CACHE[database_url] = (time.time(), schema_str)
    return schema_str


# ─────────────────────────────────────────────────────────────────────────────
# Schema catalog + per-query table retrieval (schema-linking)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_schema_smart(connector, question: str, database_url: str, limits: dict) -> str:
    """Schema string for the SQL generator, from the persistent catalog when it
    exists, with per-query table retrieval on large schemas.

    Degradation:
      - catalog empty (not crawled yet) → live introspection (_fetch_schema)
      - n <= plan inline_threshold      → all catalogued tables (everything fits)
      - else                            → top-K by embedding + 1-hop FK expansion
    """
    from models.connector_schema import ConnectorSchemaTable

    try:
        rows = ConnectorSchemaTable.query.filter_by(connector_id=connector.id).all()
    except Exception as e:
        logger.warning("Schema catalog read failed (%s) — live introspection", e)
        return _fetch_schema(database_url)

    if not rows:
        # Not crawled yet → live introspection for this question (cached in-process).
        return _fetch_schema(database_url)

    if len(rows) <= limits["inline_threshold"] or not limits["retrieval_top_k"]:
        selected = rows
    else:
        selected = _retrieve_catalog_tables(rows, question, limits)
        logger.info("Schema retrieval: %d/%d tables selected for the query",
                    len(selected), len(rows))

    return _render_catalog_schema(selected)


def _cosine(a, b) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _retrieve_catalog_tables(rows, question: str, limits: dict) -> list:
    """Top-K tables by embedding similarity to the question, plus a 1-hop FK
    expansion so join targets / association tables aren't cut off."""
    from ai.ingestion.embedder import Embedder

    k = limits["retrieval_top_k"]
    with_emb = [r for r in rows if r.embedding is not None]
    if not with_emb:
        return rows[:k]

    q_emb = Embedder().embed_single(question)
    if not q_emb:
        return with_emb[:k]

    scored = sorted(with_emb, key=lambda r: _cosine(q_emb, list(r.embedding)), reverse=True)
    top = scored[:k]
    selected = {r.table_name: r for r in top}

    if limits.get("fk_expand"):
        by_name = {r.table_name: r for r in rows}
        top_names = set(selected.keys())
        cap = k * 2

        def _add(r):
            if r is not None and len(selected) < cap:
                selected.setdefault(r.table_name, r)

        # tables referenced BY the top hits (parent side of a join)
        for r in top:
            for fk in (r.foreign_keys or []):
                _add(by_name.get(fk.get("referred_table")))
        # tables that reference a top hit (bridge / association tables)
        for r in rows:
            if any(fk.get("referred_table") in top_names for fk in (r.foreign_keys or [])):
                _add(r)

    return list(selected.values())


def _render_catalog_schema(rows) -> str:
    """Render catalogued tables into the `table(col type, ...) [FK: ...]` format
    the SQL generator expects (same shape as _fetch_schema)."""
    lines = []
    for r in rows:
        cols = ", ".join(
            f'{c["name"]} {c.get("type", "")}'.strip() for c in (r.columns or [])
        )
        line = f"{r.table_name}({cols})"
        fk_str = "; ".join(
            f"{','.join(fk.get('columns', []))} -> "
            f"{fk.get('referred_table')}({','.join(fk.get('referred_columns', []))})"
            for fk in (r.foreign_keys or []) if fk.get("referred_table")
        )
        if fk_str:
            line += f"  [FK: {fk_str}]"
        lines.append(line)
    return "\n".join(lines)


def _generate_sql(question: str, schema: str, model: str = SQL_GEN_MODEL) -> str:
    """Translate a natural-language question into a single read-only SELECT."""
    prompt = f"""Database schema. Each line is `table(column type, ...)` and may
end with `[FK: col -> other_table(col)]` describing foreign-key relationships:
{schema}

User question: {question}

Write a single read-only SQL SELECT query (PostgreSQL dialect) that answers it.
Rules:
- SELECT statements ONLY — never INSERT/UPDATE/DELETE/DROP/ALTER/etc.
- Use only tables and columns that appear in the schema above.
- JOIN tables ONLY along the [FK: ...] relationships shown. NEVER join two tables
  on columns that are not linked by a foreign key — in particular do NOT join two
  tables on their `id` columns unless an FK explicitly says so.
- Many-to-many relationships go through an association/junction table. If the two
  tables the question needs have no direct FK between them, find the table whose
  foreign keys reference BOTH and join through it. Example: users and
  organizations are linked via memberships — users.id ← memberships.user_id and
  memberships.organization_id → organizations.id — so join
  users JOIN memberships ON ... JOIN organizations ON ...
- Trace the FK path before writing joins. If no FK path connects the needed
  tables, return an empty string.
- When grouping "X by Y" (e.g. users by organization), select a Y label column
  (e.g. organizations.name) alongside the X rows and ORDER BY it.
- Do not append a trailing semicolon.
- Do not add a LIMIT clause; a row limit is applied automatically.
- If the question cannot be answered from this schema, return an empty string.

Return JSON exactly as: {{"sql": "..."}}"""

    response = get_openai_client().chat.completions.create(
        model=model or SQL_GEN_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an expert text-to-SQL engine. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
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
