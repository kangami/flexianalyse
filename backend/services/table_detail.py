"""Per-table detail for the interactive ER diagram (click a table).

Returns a one-line business description (LLM, cached) plus per-column stats:
non-null count and null count, computed by a single read-only aggregate query.

Security: the table and column names come from the introspected schema, never
from raw client input — the requested table is matched against the schema list,
so the built SQL can't be injected.
"""
import re
import time
import logging

logger = logging.getLogger(__name__)

# (db_url, table) -> (ts, description). Descriptions are structure-stable → long TTL.
_DESC_CACHE: dict[tuple, tuple[float, str]] = {}
_DESC_TTL = 24 * 3600

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _q(name: str) -> str:
    """Double-quote an SQL identifier (Postgres/standard). Names come from the
    schema and are validated as simple identifiers before use."""
    return '"' + name.replace('"', '""') + '"'


def get_table_detail(db_url: str, table: str) -> dict:
    from ai.agents.search.nodes.sql_query import fetch_tables_meta, _call_sql_tool

    tables = fetch_tables_meta(db_url, limit=100000)
    tmeta = next((t for t in tables if t.get("name") == table), None)
    if not tmeta:
        return {"error": "Unknown table"}

    cols = tmeta.get("columns", [])
    # Only profile simple identifiers (defensive; schema names normally are).
    safe_cols = [c for c in cols if _IDENT_RE.match(c.get("name", ""))]
    total = None
    non_null: dict[str, int] = {}

    if _IDENT_RE.match(table) and safe_cols:
        select = ["COUNT(*) AS __total"] + [f"COUNT({_q(c['name'])}) AS {_q(c['name'])}" for c in safe_cols]
        sql = f"SELECT {', '.join(select)} FROM {_q(table)}"
        try:
            result = _call_sql_tool("query_database", {"sql_query": sql, "limit": 1}, db_url)
            if result.get("status") == "success" and result.get("rows"):
                row = result["rows"][0]
                total = row.get("__total")
                for c in safe_cols:
                    non_null[c["name"]] = row.get(c["name"])
        except Exception as e:
            logger.warning("table stats failed for %s: %s", table, e)

    columns = []
    for c in cols:
        nn = non_null.get(c["name"])
        nulls = (total - nn) if (total is not None and nn is not None) else None
        columns.append({
            "name": c["name"],
            "type": str(c.get("type", "")),
            "pk": bool(c.get("pk")),
            "non_null": nn,
            "null_count": nulls,
        })

    return {
        "table": table,
        "description": _describe_table(db_url, table, cols, tmeta.get("foreign_keys", [])),
        "column_count": len(cols),
        "row_count": total,
        "columns": columns,
    }


def _describe_table(db_url: str, table: str, cols: list, fks: list) -> str:
    """One-sentence business purpose of the table (LLM, cached)."""
    key = (db_url, table)
    cached = _DESC_CACHE.get(key)
    if cached and (time.time() - cached[0]) < _DESC_TTL:
        return cached[1]
    try:
        from ai.observability import get_openai_client
        col_str = ", ".join(f"{c['name']} {c.get('type', '')}".strip() for c in cols[:30])
        fk_str = "; ".join(
            f"{','.join(fk.get('columns', []))} -> {fk.get('referred_table')}"
            for fk in fks if fk.get("referred_table")
        )
        prompt = (
            f"Table `{table}` — colonnes: {col_str}."
            + (f" Clés étrangères: {fk_str}." if fk_str else "")
            + " En UNE phrase courte, à quoi sert cette table (rôle métier) ? Réponds en français."
        )
        resp = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=90,
            temperature=0,
        )
        desc = (resp.choices[0].message.content or "").strip()
        _DESC_CACHE[key] = (time.time(), desc)
        return desc
    except Exception as e:
        logger.warning("table description failed for %s: %s", table, e)
        return ""
