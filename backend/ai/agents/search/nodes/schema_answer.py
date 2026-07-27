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


def build_schema_context(org_id: str, scope_connector_id: str | None, question: str) -> str:
    """Contexte factuel du schéma pour la réponse. "" si pas de catalogue."""
    from ai.agents.search.nodes.sql_query import _resolve_sql_connector
    from ai.agents.search.schema_graph import SchemaGraph
    from models.connector_schema import ConnectorSchemaTable

    connector = _resolve_sql_connector(org_id, scope_connector_id)
    if not connector:
        return ""
    rows = ConnectorSchemaTable.query.filter_by(connector_id=connector.id).all()
    if not rows:
        return ""

    visible = [r for r in rows if not getattr(r, "partition_parent", None)]
    n_partitions = len(rows) - len(visible)
    audit = [r for r in visible if getattr(r, "is_audit", False)]
    business = [r for r in visible if not getattr(r, "is_audit", False)]
    if not business:
        business = visible

    low = question.lower()
    mentioned = [
        r for r in business
        if re.search(rf"(?<![\w]){re.escape(r.table_name.lower())}(?![\w])", low)
    ]

    parts = [
        f"## Database schema — connector « {connector.name} »",
        f"{len(business)} business tables"
        + (f", {len(audit)} audit/log tables" if audit else "")
        + (f", {n_partitions} partition children (covered by their parent tables)" if n_partitions else "")
        + ".",
    ]

    if mentioned:
        parts.append("\n### Tables the question mentions (full detail)")
        for r in mentioned[:MAX_DETAILED]:
            est = f" (~{r.row_estimate:,} rows)" if r.row_estimate else ""
            parts.append(f"- {r.table_name}{est}")
            cols = ", ".join(
                f"{c['name']} {c.get('type', '')}".strip() + (" [PK]" if c.get("pk") else "")
                for c in (r.columns or [])
            )
            if cols:
                parts.append(f"  columns: {cols}")
            fks = [
                f"{','.join(fk.get('columns', []))} → {fk.get('referred_table')}"
                for fk in (r.foreign_keys or []) if fk.get("referred_table")
            ]
            if fks:
                parts.append("  foreign keys: " + "; ".join(fks))

        if len(mentioned) >= 2:
            try:
                graph = SchemaGraph([
                    {"name": r.table_name, "columns": r.columns or [], "foreign_keys": r.foreign_keys or []}
                    for r in business
                ])
                path, _ = graph.render_join_path([r.table_name for r in mentioned])
                if path:
                    parts.append(f"\n### How they are linked (real foreign-key path)\n{path}")
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
    return "\n".join(parts)
