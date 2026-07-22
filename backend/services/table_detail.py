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

# Per-column null/non-null stats need a full COUNT(col) scan. On a large table
# that scan is slow (and times out over the dial-home agent), so we only run it
# when the catalog row estimate says the table is small enough; the row count
# itself always comes from the (instant) estimate.
import os
NULL_STATS_MAX_ROWS = int(os.getenv("TABLE_DETAIL_STATS_MAX_ROWS", "200000"))


def _q(name: str) -> str:
    """Double-quote an SQL identifier (Postgres/standard). Names come from the
    schema and are validated as simple identifiers before use."""
    return '"' + name.replace('"', '""') + '"'


def get_table_detail(db_url: str, table: str, connector=None) -> dict:
    from ai.agents.search.nodes.sql_query import fetch_tables_meta, _call_sql_tool

    tmeta = _table_from_catalog(connector, table) if connector is not None else None
    if tmeta is None:
        # Not catalogued (e.g. crawl not run) → live reflection as a fallback.
        tables = fetch_tables_meta(db_url, limit=100000)
        tmeta = next((t for t in tables if t.get("name") == table), None)
    if not tmeta:
        return {"error": "Unknown table"}

    cols = tmeta.get("columns", [])
    # Row count comes from the catalog estimate (instant, no scan).
    row_estimate = tmeta.get("row_estimate")

    # Only profile simple identifiers (defensive; schema names normally are).
    safe_cols = [c for c in cols if _IDENT_RE.match(c.get("name", ""))]
    scanned_total = None
    non_null: dict[str, int] = {}
    stats_skipped = False

    small_enough = row_estimate is not None and row_estimate <= NULL_STATS_MAX_ROWS
    if _IDENT_RE.match(table) and safe_cols and small_enough:
        select = ["COUNT(*) AS __total"] + [f"COUNT({_q(c['name'])}) AS {_q(c['name'])}" for c in safe_cols]
        sql = f"SELECT {', '.join(select)} FROM {_q(table)}"
        try:
            result = _call_sql_tool("query_database", {"sql_query": sql, "limit": 1}, db_url)
            if result.get("status") == "success" and result.get("rows"):
                row = result["rows"][0]
                scanned_total = row.get("__total")
                for c in safe_cols:
                    non_null[c["name"]] = row.get(c["name"])
        except Exception as e:
            logger.warning("table stats failed for %s: %s", table, e)
    elif safe_cols:
        # Table too large (or size unknown) — skip the full scan; show columns
        # without null stats rather than risk a timeout.
        stats_skipped = True

    columns = []
    for c in cols:
        nn = non_null.get(c["name"])
        nulls = (scanned_total - nn) if (scanned_total is not None and nn is not None) else None
        columns.append({
            "name": c["name"],
            "type": str(c.get("type", "")),
            "pk": bool(c.get("pk")),
            "non_null": nn,
            "null_count": nulls,
        })

    # Prefer the exact scanned count when we computed it, else the estimate.
    row_count = scanned_total if scanned_total is not None else row_estimate

    return {
        "table": table,
        "description": _describe_table(db_url, table, cols, tmeta.get("foreign_keys", [])),
        "column_count": len(cols),
        "row_count": row_count,
        "row_estimated": scanned_total is None and row_estimate is not None,
        "stats_skipped": stats_skipped,
        "columns": columns,
    }


def _table_from_catalog(connector, table: str) -> dict | None:
    """One table's meta from the persistent catalog — avoids a full live schema
    reflection (hundreds of tables) on every click. Returns None if not found."""
    try:
        from models.connector_schema import ConnectorSchemaTable
        row = ConnectorSchemaTable.query.filter_by(
            connector_id=connector.id, table_name=table
        ).first()
        if not row:
            return None
        return {
            "name": row.table_name,
            "columns": [
                {"name": c["name"], "type": str(c.get("type", "")), "pk": bool(c.get("pk") or c.get("is_primary_key"))}
                for c in (row.columns or [])
            ],
            "foreign_keys": row.foreign_keys or [],
            "row_estimate": row.row_estimate,
        }
    except Exception as e:
        logger.warning("catalog lookup failed for %s: %s", table, e)
        return None


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
