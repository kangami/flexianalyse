"""Crawl + stockage du catalogue de schéma d'un connecteur SQL.

Introspecte la base une fois (via le serveur MCP, réflexion en masse), embed
chaque table pour le retrieval, puis remplace le catalogue dans
`connector_schema_tables`. Découple l'introspection du temps de requête et
alimente la sélection de tables par requête (schema-linking) sur les grosses
bases.

Le plafond de tables cataloguées dépend du plan de l'organisation (voir
config/plans.py). Tourne dans le worker Celery — l'embedder (objet lourd) est
donc créé ici, jamais à l'import.
"""
import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import OperationalError

from config.extensions import db
from config.plans import plan_limits
from models.connector import Connector
from models.organization import Organization
from models.connector_schema import ConnectorSchemaTable

logger = logging.getLogger(__name__)

# Repli quand le plan n'impose pas de plafond (entreprise) : on borne quand même
# à un très grand nombre pour ne pas rapatrier un schéma pathologique d'un coup.
UNLIMITED_CAP = 100_000

# Écrit le catalogue par petits lots : un unique INSERT de 2000+ lignes portant
# chacune un vecteur(1536) peut faire redémarrer une petite instance Postgres, et
# des commits courts et fréquents empêchent la connexion de mourir pendant le crawl.
INSERT_CHUNK = 250
COMMIT_RETRIES = 3


def _run_with_retry(label: str, work) -> None:
    """Exécute `work()` puis commit, en tolérant une coupure Postgres transitoire.

    Sur une grosse base, Render peut couper la connexion inactive (SSL EOF) ou
    passer la base en recovery mode pendant le crawl. On rollback et on réessaie ;
    pool_pre_ping fournit une connexion neuve au commit suivant. Les objets ORM du
    lot (PK uuid côté client) sont re-`add`-és tels quels, rien n'ayant été persisté.
    """
    for attempt in range(1, COMMIT_RETRIES + 1):
        try:
            work()
            db.session.commit()
            return
        except OperationalError as e:
            db.session.rollback()
            if attempt == COMMIT_RETRIES:
                raise
            wait = 2 ** attempt
            logger.warning(
                "Commit '%s' échoué (tentative %d/%d): %r — nouvel essai dans %ds",
                label, attempt, COMMIT_RETRIES, e, wait,
            )
            time.sleep(wait)


def table_descriptor(meta: dict) -> str:
    """Texte descriptif d'une table pour l'embedding (nom + colonnes + FK).

    Pas de valeurs d'exemple en v1 (plus simple, moins sensible)."""
    cols = ", ".join(f"{c['name']} ({c.get('type', '')})" for c in meta.get("columns", []))
    text = f"Table {meta['name']}. Colonnes: {cols}."
    fks = [
        f"{','.join(fk.get('columns', []))} -> {fk.get('referred_table')}"
        for fk in meta.get("foreign_keys", []) if fk.get("referred_table")
    ]
    if fks:
        text += " Clés étrangères: " + "; ".join(fks) + "."
    return text


def crawl_connector_schema(connector_id: str, org_id: str) -> dict:
    """Introspecte et (re)catalogue le schéma d'un connecteur SQL.

    Renvoie {status, table_count}. Met à jour l'état de crawl sur le connecteur.
    """
    from ai.agents.search.nodes.sql_query import _get_database_url, fetch_tables_meta
    from ai.ingestion.embedder import Embedder

    connector = Connector.query.get(UUID(connector_id))
    if not connector:
        return {"status": "error", "reason": "connector not found"}
    if connector.type != "sql":
        return {"status": "skipped", "reason": "not a SQL connector"}

    connector.schema_crawl_status = "running"
    db.session.commit()

    try:
        db_url = _get_database_url(org_id, connector_id)
        if not db_url:
            raise ValueError("no database URL for connector")

        org = Organization.query.get(UUID(org_id))
        cap = plan_limits(org.plan if org else None)["catalog_max"]
        tables = fetch_tables_meta(db_url, limit=cap if cap is not None else UNLIMITED_CAP)

        # Embed chaque descriptif de table (batché). AUCUN accès DB pendant ce
        # temps : l'embedding peut durer des dizaines de secondes et la connexion
        # ne doit pas rester ouverte inactive.
        descriptors = [table_descriptor(t) for t in tables]
        embeddings = Embedder().embed_chunks(descriptors) if descriptors else []

        from services.audit_tables import is_audit_table

        now = datetime.now(timezone.utc)
        rows = [
            ConnectorSchemaTable(
                connector_id=UUID(connector_id),
                organization_id=UUID(org_id),
                table_name=meta["name"],
                columns=meta.get("columns", []),
                primary_keys=[c["name"] for c in meta.get("columns", []) if c.get("pk")],
                foreign_keys=meta.get("foreign_keys", []),
                row_estimate=meta.get("row_estimate"),
                is_audit=is_audit_table(meta["name"]),
                embedding=emb,
                introspected_at=now,
            )
            for meta, emb in zip(tables, embeddings)
        ]

        # Remplace le catalogue par lots. La purge est incluse dans le 1er commit
        # (delete + premières lignes atomiques) pour ne pas laisser le connecteur
        # sans catalogue si un lot suivant échoue.
        if not rows:
            _run_with_retry(
                "purge-catalogue-vide",
                lambda: ConnectorSchemaTable.query.filter_by(connector_id=UUID(connector_id)).delete(),
            )
        else:
            for i in range(0, len(rows), INSERT_CHUNK):
                chunk = rows[i:i + INSERT_CHUNK]

                def _work(chunk=chunk, first=(i == 0)):
                    if first:
                        ConnectorSchemaTable.query.filter_by(connector_id=UUID(connector_id)).delete()
                    db.session.add_all(chunk)

                _run_with_retry(f"catalogue[{i}:{i + len(chunk)}]", _work)

        # Re-fetch : la session a pu expirer/rollback l'instance au fil des commits.
        connector = Connector.query.get(UUID(connector_id))
        if connector:
            connector.schema_crawl_status = "done"
            connector.schema_crawled_at = now
            connector.schema_table_count = len(tables)
        _run_with_retry("statut-crawl", lambda: None)
        logger.info("Schema catalog: connector %s → %d tables", connector_id, len(tables))
        return {"status": "done", "table_count": len(tables)}

    except Exception as e:
        db.session.rollback()
        # Recharge (la session a rollback) pour poser l'état d'échec.
        connector = Connector.query.get(UUID(connector_id))
        if connector:
            connector.schema_crawl_status = "failed"
            db.session.commit()
        logger.error("Schema crawl failed for connector %s: %r", connector_id, e)
        return {"status": "failed", "reason": str(e)}
