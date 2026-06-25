# knowledge_graph.py
import uuid
from datetime import datetime, timezone
import os
from config.extensions import db
from pgvector.sqlalchemy import Vector

EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))


class KGNode(db.Model):
    """A node in the org knowledge graph."""
    __tablename__ = 'kg_nodes'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    org_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    node_type = db.Column(db.String, nullable=False)  # 'document', 'table', 'folder', 'person', 'concept'
    external_id = db.Column(db.String, nullable=True)  # Drive file_id, table name, etc.
    connector_type = db.Column(db.String, nullable=True)  # 'google_drive', 'sql', 'dropbox'
    name = db.Column(db.String, nullable=False)
    kgnode_metadata = db.Column(db.JSON, nullable=True)
    embedding = db.Column(Vector(int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relations
    outgoing_edges = db.relationship(
        'KGEdge',
        foreign_keys='KGEdge.source_id',
        backref='source_node',
        lazy='dynamic'
    )
    incoming_edges = db.relationship(
        'KGEdge',
        foreign_keys='KGEdge.target_id',
        backref='target_node',
        lazy='dynamic'
    )


class KGEdge(db.Model):
    """An edge (relationship) between two nodes."""
    __tablename__ = 'kg_edges'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    org_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    source_id = db.Column(db.Uuid, db.ForeignKey('kg_nodes.id'), nullable=False)
    target_id = db.Column(db.Uuid, db.ForeignKey('kg_nodes.id'), nullable=False)
    relation = db.Column(db.String, nullable=False)  # 'CONTAINS', 'REFERENCES', 'MENTIONS', 'RELATED_TO'
    weight = db.Column(db.Float, default=1.0)
    kgedge_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))