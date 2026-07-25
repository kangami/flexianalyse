"""Build the Database Report for a SQL connector.

V1 principle: relevance over exhaustiveness — every figure is MEASURED (catalog
stats + the FK graph), nothing fabricated. Sections: overview, top critical
tables (FK in-degree), architecture, and only the health dimensions we can defend
(Schema Design, Documentation, FK indexing), plus an AI summary that is told to
cite ONLY the numbers computed here.

Runs in the Celery worker (chained to the schema crawl or on demand). Heavy
introspection is a single instant `database_stats` round-trip; the rest is graph
math over the catalogue.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Weights of the measured health dimensions (shown in the UI). Renormalised over
# the dimensions actually available for the engine.
WEIGHTS = {"schema_design": 0.40, "documentation": 0.30, "fk_index": 0.30}


def _pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def build_connector_report(connector_id: str, org_id: str) -> dict:
    from uuid import UUID
    from models.connector_schema import ConnectorSchemaTable
    from ai.agents.search.schema_graph import SchemaGraph
    from ai.agents.search.nodes.sql_query import (
        _get_database_url, _call_sql_tool, SCHEMA_FETCH_TIMEOUT,
    )

    db_url = _get_database_url(org_id, connector_id)
    if not db_url:
        raise ValueError("no database URL for connector")

    # 1. Instant catalog stats (per-dialect, n/a where unsupported).
    res = _call_sql_tool("database_stats", {}, db_url, timeout=SCHEMA_FETCH_TIMEOUT)
    if res.get("status") != "success":
        raise RuntimeError(res.get("message", "database_stats failed"))
    engine = res.get("engine")
    version = res.get("version")
    m = res.get("metrics", {}) or {}

    # 2. The catalogued schema → FK graph.
    rows = ConnectorSchemaTable.query.filter_by(connector_id=UUID(connector_id)).all()
    tables = [
        {"name": r.table_name, "columns": r.columns or [], "foreign_keys": r.foreign_keys or []}
        for r in rows
    ]
    graph = SchemaGraph(tables)
    catalogued = len(rows)
    with_pk = sum(1 for r in rows if r.primary_keys)
    est_rows = sum(int(r.row_estimate) for r in rows if r.row_estimate)
    row_est = {r.table_name: int(r.row_estimate) for r in rows if r.row_estimate is not None}

    ref_by = graph.referenced_by()
    orphans = graph.orphans()
    junctions = graph.junctions()

    # 3. Overview — prefer true DB stats, fall back to the catalogue.
    overview = {
        "schemas": m.get("schemas"),
        "tables": m.get("tables") if m.get("tables") is not None else catalogued,
        "columns": m.get("columns"),
        "views": m.get("views"),
        "materialized_views": m.get("materialized_views"),
        "sequences": m.get("sequences"),
        "functions": m.get("functions"),
        "procedures": m.get("procedures"),
        "triggers": m.get("triggers"),
        "foreign_keys": m.get("foreign_keys"),
        "indexes": m.get("indexes"),
        "db_size_bytes": m.get("db_size_bytes"),
        "estimated_rows": est_rows or None,
        "catalogued_tables": catalogued,
        "capped": bool(m.get("tables") and catalogued < m.get("tables")),
    }

    # 4. Critical tables — FK in-degree.
    critical = sorted(
        ({"table": t, "referenced_by": c, "rows": row_est.get(t)} for t, c in ref_by.items() if c > 0),
        key=lambda x: x["referenced_by"], reverse=True,
    )[:10]

    # 5. Architecture.
    domains = []
    for comp in graph.components():
        if len(comp) < 3:
            continue
        anchor = max(comp, key=lambda t: ref_by.get(t, 0))
        domains.append({"name": anchor, "tables": len(comp)})
    architecture = {
        "hub_tables": critical[:5],
        "junction_tables": {"count": len(junctions), "sample": junctions[:8]},
        "orphan_tables": {"count": len(orphans), "sample": orphans[:8]},
        "domains": domains[:8],
    }

    # 6. Measured health dimensions.
    dims = []

    # Schema Design — PK coverage + orphan penalty.
    if catalogued:
        pk_cov = with_pk / catalogued
        orphan_ratio = len(orphans) / catalogued
        sd_score = round(100 * (0.75 * pk_cov + 0.25 * (1 - orphan_ratio)))
        dims.append({
            "key": "schema_design", "label": "Schema Design", "score": sd_score,
            "checks": [
                {"label": "Tables with a primary key", "value": f"{_pct(with_pk, catalogued)}% ({with_pk}/{catalogued})"},
                {"label": "Tables without a primary key", "value": catalogued - with_pk},
                {"label": "Orphan tables (no relations)", "value": len(orphans)},
            ],
        })

    # Documentation — comment coverage (n/a if the engine didn't report it).
    dt, dc = m.get("documented_tables"), m.get("documented_columns")
    tot_t, tot_c = m.get("tables") or catalogued, m.get("columns")
    if dt is not None and tot_t:
        t_ratio = dt / tot_t
        c_ratio = (dc / tot_c) if (dc is not None and tot_c) else t_ratio
        doc_score = round(100 * (0.5 * t_ratio + 0.5 * c_ratio))
        checks = [{"label": "Tables documented", "value": f"{_pct(dt, tot_t)}% ({dt}/{tot_t})"}]
        if dc is not None and tot_c:
            checks.append({"label": "Columns documented", "value": f"{_pct(dc, tot_c)}% ({dc}/{tot_c})"})
        dims.append({"key": "documentation", "label": "Documentation", "score": doc_score, "checks": checks})

    # FK indexing — foreign keys backed by a covering index (n/a where unsupported).
    fk_total, fk_bad = m.get("foreign_keys"), m.get("fk_without_index")
    if fk_bad is not None and fk_total:
        fk_score = round(100 * (1 - fk_bad / fk_total))
        dims.append({
            "key": "fk_index", "label": "FK Indexing", "score": fk_score,
            "checks": [
                {"label": "Foreign keys without an index", "value": fk_bad},
                {"label": "Total foreign keys", "value": fk_total},
            ],
        })

    # Global = weighted average over available dimensions (renormalised).
    avail = [d for d in dims if d.get("score") is not None]
    wsum = sum(WEIGHTS[d["key"]] for d in avail)
    global_score = round(sum(d["score"] * WEIGHTS[d["key"]] for d in avail) / wsum) if wsum else None
    health = {"score": global_score, "weights": WEIGHTS, "dimensions": dims}

    # 7. AI summary + recommendations — grounded strictly in the numbers above.
    summary, recommendations = _ai_summary(engine, version, overview, health, critical, architecture)

    return {
        "engine": engine,
        "version": version,
        "overview": overview,
        "health": health,
        "critical_tables": critical,
        "architecture": architecture,
        "summary": summary,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _ai_summary(engine, version, overview, health, critical, architecture):
    import json
    from ai.observability import get_openai_client
    facts = {
        "engine": engine, "version": version, "overview": overview,
        "health": health, "top_critical_tables": critical, "architecture": architecture,
    }
    prompt = (
        "You are a database analyst. Using ONLY the measured facts below (do not "
        "invent any number or table name), write:\n"
        "1) a 3-4 sentence executive summary of this database's state, and\n"
        "2) 3 to 6 concrete recommendations, each tied to a specific measured "
        "figure (e.g. tables without a primary key, undocumented tables, foreign "
        "keys without an index, orphan tables).\n"
        "Be factual and concise. Return JSON: "
        '{"summary": "...", "recommendations": ["...", "..."]}.\n\n'
        f"MEASURED FACTS:\n{json.dumps(facts, default=str)[:6000]}"
    )
    try:
        resp = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You analyse databases from measured facts only. Return valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        recs = [str(r).strip() for r in (data.get("recommendations") or []) if str(r).strip()]
        return str(data.get("summary", "")).strip(), recs[:6]
    except Exception as e:
        logger.warning("Report AI summary failed: %s", e)
        return "", []
