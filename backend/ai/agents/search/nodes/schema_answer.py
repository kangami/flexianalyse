"""Questions de compréhension du schéma — réponse depuis le catalogue, sans SQL.

« Quelles tables ai-je ? », « comment customer est lié à payment ? », « décris la
table rental » : les faits sont déjà dans le catalogue (tables, colonnes, FK,
rôles) et le SchemaGraph (chemins de jointure). On assemble un contexte factuel
et le modèle rédige l'explication — zéro requête SQL, zéro hallucination.
"""
import logging
import re

logger = logging.getLogger(__name__)

MAX_LISTED_TABLES = 150
MAX_DETAILED = 6
MAX_ADVICE_TABLES = 60


def _table_detail_lines(r) -> list[str]:
    est = f" (~{r.row_estimate:,} rows)" if r.row_estimate else ""
    lines = [f"- {r.table_name}{est}"]
    cols = ", ".join(
        f"{c['name']} {c.get('type', '')}".strip() + (" [PK]" if c.get("pk") else "")
        for c in (r.columns or [])
    )
    if cols:
        lines.append(f"  columns: {cols}")
    fks = [
        f"{','.join(fk.get('columns', []))} → {fk.get('referred_table')}"
        for fk in (r.foreign_keys or []) if fk.get("referred_table")
    ]
    if fks:
        lines.append("  foreign keys: " + "; ".join(fks))
    return lines


def _mentioned_tables(business: list, question: str) -> list:
    low = question.lower()
    return [
        r for r in business
        if re.search(rf"(?<![\w]){re.escape(r.table_name.lower())}(?![\w])", low)
    ]


def build_schema_context(org_id: str, scope_connector_id: str | None, question: str) -> tuple[str, list[str]]:
    """(contexte factuel du schéma, tables à surligner sur le diagramme).

    Les tables retournées sont celles de la question + le chemin de jointure qui
    les relie — le frontend bascule sur le diagramme ER et anime ce chemin.
    ("", []) si pas de catalogue."""
    from ai.agents.search.nodes.sql_query import _resolve_sql_connector
    from ai.agents.search.schema_graph import SchemaGraph
    from models.connector_schema import ConnectorSchemaTable

    connector = _resolve_sql_connector(org_id, scope_connector_id)
    if not connector:
        return "", []
    rows = ConnectorSchemaTable.query.filter_by(connector_id=connector.id).all()
    if not rows:
        return "", []

    visible = [r for r in rows if not getattr(r, "partition_parent", None)]
    n_partitions = len(rows) - len(visible)
    audit = [r for r in visible if getattr(r, "is_audit", False)]
    business = [r for r in visible if not getattr(r, "is_audit", False)]
    if not business:
        business = visible

    mentioned = _mentioned_tables(business, question)

    parts = [
        f"## Database schema — connector « {connector.name} »",
        f"{len(business)} business tables"
        + (f", {len(audit)} audit/log tables" if audit else "")
        + (f", {n_partitions} partition children (covered by their parent tables)" if n_partitions else "")
        + ".",
    ]

    focus = [r.table_name for r in mentioned]

    if mentioned:
        parts.append("\n### Tables the question mentions (full detail)")
        for r in mentioned[:MAX_DETAILED]:
            parts.extend(_table_detail_lines(r))

        if len(mentioned) >= 2:
            try:
                graph = SchemaGraph([
                    {"name": r.table_name, "columns": r.columns or [], "foreign_keys": r.foreign_keys or []}
                    for r in business
                ])
                path, on_tables = graph.render_join_path([r.table_name for r in mentioned])
                if path:
                    parts.append(f"\n### How they are linked (real foreign-key path)\n{path}")
                    focus = [t for t in on_tables if t] or focus
            except Exception as e:
                logger.warning("Join path for schema answer failed: %s", e)

    parts.append("\n### All business tables")
    for r in business[:MAX_LISTED_TABLES]:
        est = f" (~{r.row_estimate:,} rows)" if r.row_estimate else ""
        junction = " — junction table (N:N)" if getattr(r, "table_role", "") == "junction" else ""
        parts.append(f"- {r.table_name}{est} — {len(r.columns or [])} columns{junction}")
    if len(business) > MAX_LISTED_TABLES:
        parts.append(f"...and {len(business) - MAX_LISTED_TABLES} more tables.")

    parts.append(
        "\nINSTRUCTIONS: the user asked about the database STRUCTURE. Answer with a "
        "clear explanation of the schema (tables, columns, relationships) based ONLY "
        "on the facts above — never invent tables or columns, and do not show row data."
    )
    return "\n".join(parts), focus


def build_advice_context(org_id: str, scope_connector_id: str | None, question: str) -> str:
    """Contexte consultatif (domaine + tables clés + questions types) pour les
    questions de conseil : analyses possibles, KPI, qualité de données. "" si pas
    de catalogue."""
    from ai.agents.search.nodes.sql_query import _resolve_sql_connector
    from models.connector_schema import ConnectorSchemaTable

    connector = _resolve_sql_connector(org_id, scope_connector_id)
    if not connector:
        return ""
    rows = ConnectorSchemaTable.query.filter_by(connector_id=connector.id).all()
    business = [
        r for r in rows
        if not getattr(r, "partition_parent", None) and not getattr(r, "is_audit", False)
    ]
    if not business:
        return ""

    parts = [f"## Database advisory context — connector « {connector.name} »"]

    # Domaine inféré + questions types (cachés 1 h ; déjà chauds via le diagramme).
    try:
        from ai.agents.db_analysis import get_db_insights
        insights = get_db_insights(org_id, scope_connector_id)
        if insights.get("domain"):
            parts.append(f"Inferred business domain: {insights['domain']}")
        if insights.get("questions"):
            parts.append("Questions this database is known to answer well:")
            parts.extend(f"- {q}" for q in insights["questions"])
    except Exception as e:
        logger.warning("DB insights unavailable for advice: %s", e)

    mentioned = _mentioned_tables(business, question)
    if mentioned:
        parts.append("\n### Tables the question mentions (full detail)")
        for r in mentioned[:MAX_DETAILED]:
            parts.extend(_table_detail_lines(r))

    parts.append("\n### Main tables (largest first)")
    ranked = sorted(business, key=lambda r: r.row_estimate or 0, reverse=True)
    for r in ranked[:MAX_ADVICE_TABLES]:
        est = f" ~{r.row_estimate:,} rows, " if r.row_estimate else " "
        junction = " — junction table (N:N)" if getattr(r, "table_role", "") == "junction" else ""
        parts.append(f"- {r.table_name} ({est}{len(r.columns or [])} columns){junction}")
    if len(business) > MAX_ADVICE_TABLES:
        parts.append(f"...and {len(business) - MAX_ADVICE_TABLES} more tables.")

    parts.append(
        "\nINSTRUCTIONS: the user wants ADVICE about their data (analyses to run, "
        "KPIs, data quality, modeling). Answer as a pragmatic data consultant: give "
        "concrete, prioritized recommendations grounded ONLY in the tables and "
        "columns above, naming for each the exact tables (and columns when relevant) "
        "to use — and, when helpful, the question the user could ask this assistant "
        "next to get the numbers. Never invent tables or columns; show no row data."
    )
    return "\n".join(parts)
