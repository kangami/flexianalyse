"""
DB Analysis Agent
=================
Understands a connected SQL database in the background and produces, for the UI:

  - schema_mermaid : a Mermaid `erDiagram` of tables + columns + FK relationships,
                     built deterministically from introspection (no LLM, exact).
  - domain         : the inferred business domain (one LLM call).
  - questions      : 4 anticipated business questions the user is likely to ask,
                     each answerable by a single SQL SELECT (same LLM call).

Runs in the API process (like the Text-to-SQL node) and talks to the SQL MCP
server synchronously. Results are cached per database URL to avoid re-running the
LLM / re-introspecting on every page load.
"""
import os
import re
import json
import time
import logging

from ai.observability import get_openai_client
# Reuse the connector resolution + batched schema fetch used by Text-to-SQL.
from ai.agents.search.nodes.sql_query import (
    _get_database_url, fetch_tables_meta, _org_plan_limits,
)

logger = logging.getLogger(__name__)

INSIGHTS_MODEL = os.getenv("DB_INSIGHTS_MODEL", "gpt-4o")
# The ER diagram shows every table the plan allows (like the /schema endpoint);
# only the LLM domain/questions prompt stays bounded (sending hundreds of tables
# is wasteful and blows the token budget). Enterprise (catalog_max=None) is
# capped by DIAGRAM_HARD_MAX so a multi-thousand-table DB can't hang Mermaid.
LLM_MAX_TABLES = int(os.getenv("DB_INSIGHTS_LLM_TABLES", "40"))
DIAGRAM_HARD_MAX = int(os.getenv("DB_INSIGHTS_DIAGRAM_MAX", "1000"))
MAX_COLS_PER_TABLE = 20

# database_url -> (timestamp, insights dict)
_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 3600  # 1 hour — schema changes are picked up after that


def get_db_insights(org_id: str, connector_id: str | None = None) -> dict:
    """Return {domain, questions, schema_mermaid} for the org's SQL connector."""
    db_url = _get_database_url(org_id, connector_id)
    if not db_url:
        return {"domain": "", "questions": [], "schema_mermaid": "", "error": "No active SQL connector"}

    cached = _CACHE.get(db_url)
    if cached and (time.time() - cached[0]) < _TTL:
        return cached[1]

    # Diagram cap follows the plan (free 15 / pro 150 / business 500 / enterprise
    # unlimited → DIAGRAM_HARD_MAX), so the ER diagram shows what the sync catalogued.
    cap = _org_plan_limits(org_id).get("catalog_max")
    diagram_cap = DIAGRAM_HARD_MAX if cap is None else min(cap, DIAGRAM_HARD_MAX)

    try:
        tables = _introspect(db_url, diagram_cap)
    except Exception as e:
        logger.error("DB introspection failed: %s", e, exc_info=True)
        return {"domain": "", "questions": [], "schema_mermaid": "", "error": "Could not read the database schema"}

    if not tables:
        return {"domain": "", "questions": [], "schema_mermaid": "", "error": "No tables found"}

    mermaid = _build_mermaid_er(tables)
    # The LLM only needs a representative sample to infer the domain + questions.
    domain, questions = _llm_domain_and_questions(tables[:LLM_MAX_TABLES])

    result = {"domain": domain, "questions": questions, "schema_mermaid": mermaid}
    _CACHE[db_url] = (time.time(), result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Introspection
# ─────────────────────────────────────────────────────────────────────────────

def _introspect(db_url: str, limit: int) -> list[dict]:
    """[{name, columns:[{name,type,pk}], fks:[{columns,referred_table}]}] per table.
    One batched round-trip via the shared fetch_tables_meta."""
    out = []
    for t in fetch_tables_meta(db_url, limit=limit)[:limit]:
        out.append({
            "name": t["name"],
            "columns": t["columns"],
            "fks": [
                {"columns": fk.get("columns", []), "referred_table": fk.get("referred_table")}
                for fk in t.get("foreign_keys", []) if fk.get("referred_table")
            ],
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Mermaid ER diagram (deterministic)
# ─────────────────────────────────────────────────────────────────────────────

def _san(identifier: str) -> str:
    """Mermaid-safe identifier: alphanumerics + underscore only."""
    s = re.sub(r"\W+", "_", str(identifier or "")).strip("_")
    return s or "unnamed"


def _san_type(sql_type: str) -> str:
    """First token of the type, without parens/args — e.g. VARCHAR(255) -> VARCHAR."""
    t = str(sql_type or "").split("(")[0].split()[0] if sql_type else "text"
    return re.sub(r"\W+", "_", t) or "text"


# Above this many tables, show only key columns (PK/FK) per entity so the Mermaid
# source stays small enough to render — a full column list × hundreds of tables
# overflows the renderer and is unreadable anyway. Relationships are kept intact.
SLIM_TABLE_THRESHOLD = int(os.getenv("DB_INSIGHTS_SLIM_ABOVE", "60"))


def _build_mermaid_er(tables: list[dict]) -> str:
    """Emit a Mermaid erDiagram from tables + columns + foreign keys."""
    present = {t["name"] for t in tables}
    name_map = {t["name"]: _san(t["name"]) for t in tables}
    # FK columns per table, to tag them with FK in the attribute list.
    fk_cols = {
        t["name"]: {c for fk in t["fks"] for c in fk.get("columns", [])}
        for t in tables
    }
    slim = len(tables) > SLIM_TABLE_THRESHOLD

    lines = ["erDiagram"]

    for t in tables:
        ent = name_map[t["name"]]
        keys = fk_cols[t["name"]]
        cols = t["columns"]
        if slim:
            # Keep only primary/foreign keys; fall back to the first column so an
            # entity is never rendered empty.
            cols = [c for c in cols if c["pk"] or c["name"] in keys] or cols[:1]
        lines.append(f"    {ent} {{")
        for col in cols[:MAX_COLS_PER_TABLE]:
            key = "PK" if col["pk"] else ("FK" if col["name"] in keys else "")
            attr = f"        {_san_type(col['type'])} {_san(col['name'])}"
            if key:
                attr += f" {key}"
            lines.append(attr)
        lines.append("    }")

    # Relationships: child.fk -> parent.pk  ⇒  PARENT ||--o{ CHILD
    seen = set()
    for t in tables:
        child = name_map[t["name"]]
        for fk in t["fks"]:
            ref = fk.get("referred_table")
            if ref not in present:
                continue
            parent = name_map[ref]
            edge = (parent, child)
            if edge in seen:
                continue
            seen.add(edge)
            label = _san(fk["columns"][0]) if fk.get("columns") else "ref"
            lines.append(f'    {parent} ||--o{{ {child} : "{label}"')

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Domain + anticipated questions (one cached LLM call)
# ─────────────────────────────────────────────────────────────────────────────

def _schema_text(tables: list[dict]) -> str:
    lines = []
    for t in tables:
        cols = ", ".join(f"{c['name']} {_san_type(c['type'])}" for c in t["columns"][:MAX_COLS_PER_TABLE])
        line = f"{t['name']}({cols})"
        fks = "; ".join(
            f"{','.join(fk.get('columns', []))} -> {fk['referred_table']}"
            for fk in t["fks"] if fk.get("referred_table")
        )
        if fks:
            line += f"  [FK: {fks}]"
        lines.append(line)
    return "\n".join(lines)


def _llm_domain_and_questions(tables: list[dict]) -> tuple[str, list[str]]:
    prompt = f"""You are a data analyst inspecting a database schema. Each line is
`table(column type, ...)` optionally ending with `[FK: col -> other_table]`:

{_schema_text(tables)}

1. Infer the business domain this database was built for (one short sentence).
2. Propose EXACTLY 4 concise, business-relevant questions a user of this system
   would realistically ask, each answerable by a single read-only SQL SELECT over
   this schema. Prefer aggregates and joins that reflect the domain. Keep each
   question under 12 words.

Return JSON exactly as: {{"domain": "...", "questions": ["...", "...", "...", "..."]}}"""

    try:
        resp = get_openai_client().chat.completions.create(
            model=INSIGHTS_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You analyse database schemas. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )
        data = json.loads(resp.choices[0].message.content)
        domain = str(data.get("domain", "")).strip()
        questions = [str(q).strip() for q in (data.get("questions") or []) if str(q).strip()][:4]
        return domain, questions
    except Exception as e:
        logger.warning("DB insights LLM step failed: %s", e)
        return "", []
