import uuid
from datetime import datetime
from config.extensions import db


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class ResourceBinding(db.Model):
    """Binding sécurité entre ressource et périmètre outil."""
    __tablename__ = 'resource_bindings'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    resource_id = db.Column(db.Uuid, db.ForeignKey('resources.id'), nullable=False)
    tool_scope_id = db.Column(db.Uuid, db.ForeignKey('tool_scopes.id'), nullable=False)
    access_level = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
