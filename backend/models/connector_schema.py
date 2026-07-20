import uuid
import os
from datetime import datetime, timezone
from config.extensions import db
from pgvector.sqlalchemy import Vector


class ConnectorSchemaTable(db.Model):
    """Catalogue de schéma persistant d'un connecteur SQL.

    Une ligne par table de la base connectée : colonnes, clés primaires/étrangères
    introspectées une fois (crawl Celery) puis réutilisées, plus un embedding du
    descriptif de la table pour la sélection de tables par requête (schema-linking)
    sur les grosses bases. Découple l'introspection du temps de requête et permet
    de passer à l'échelle sans tout envoyer au LLM.
    """
    __tablename__ = 'connector_schema_tables'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    connector_id = db.Column(
        db.Uuid, db.ForeignKey('connectors.id', ondelete='CASCADE'), nullable=False, index=True
    )
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    table_name = db.Column(db.String, nullable=False)
    columns = db.Column(db.JSON, nullable=True)        # [{name, type, pk}]
    primary_keys = db.Column(db.JSON, nullable=True)   # [col, ...]
    foreign_keys = db.Column(db.JSON, nullable=True)   # [{columns, referred_table, referred_columns}]
    row_estimate = db.Column(db.BigInteger, nullable=True)
    embedding = db.Column(Vector(int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))), nullable=True)
    introspected_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('connector_id', 'table_name', name='uq_connector_table'),
    )
