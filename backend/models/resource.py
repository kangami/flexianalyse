import uuid
import os
from datetime import datetime
from config.extensions import db
from pgvector.sqlalchemy import Vector

class Resource(db.Model):
    """Ressource unifiée (fichier, ticket, message, doc...)."""
    __tablename__ = 'resources'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    connector_id = db.Column(db.Uuid, db.ForeignKey('connectors.id'), nullable=True)
    external_id = db.Column(db.String, nullable=True)
    type = db.Column(db.String, nullable=True)
    title = db.Column(db.String, nullable=True)
    ressource_metadata = db.Column(db.JSON, default=dict)
    
    # Versionning — skip si le fichier n'a pas changé depuis le sync
    content_hash = db.Column(db.String, nullable=True)       # SHA256 du contenu brut
    external_modified_at = db.Column(db.DateTime, nullable=True)  # last_modified venant de Drive/Dropbox
    external_version = db.Column(db.String, nullable=True)   # version ID Drive (headRevisionId) ou Dropbox (rev)
    file_size_bytes = db.Column(db.BigInteger, nullable=True)

    # Ingestion status
    ingestion_status = db.Column(db.String, default='pending')  # pending, processing, done, failed, skipped
    ingestion_error = db.Column(db.Text, nullable=True)
    ingested_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    chunks = db.relationship('ResourceChunk', backref='resource', lazy='dynamic', cascade='all, delete-orphan')


class ResourceChunk(db.Model):
    """Chunk de contenu d'une ressource avec embedding."""
    __tablename__ = 'resource_chunks'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    resource_id = db.Column(db.Uuid, db.ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    connector_id = db.Column(db.Uuid, db.ForeignKey('connectors.id'), nullable=True)

    # Contenu
    content = db.Column(db.Text, nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    chunk_type = db.Column(db.String, nullable=True)      # 'text', 'table', 'title', 'code'

    # Embedding
    embedding = db.Column(Vector(int(os.getenv('EMBEDDING_DIMENSIONS', '1536'))), nullable=True)

    # Metadata
    page_number = db.Column(db.Integer, nullable=True)
    section_title = db.Column(db.String, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    chunk_metadata = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResourceBinding(db.Model):
    """Binding sécurité entre ressource et périmètre outil."""
    __tablename__ = 'resource_bindings'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    resource_id = db.Column(db.Uuid, db.ForeignKey('resources.id'), nullable=False)
    tool_scope_id = db.Column(db.Uuid, db.ForeignKey('tool_scopes.id'), nullable=False)
    access_level = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
