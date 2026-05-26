import uuid
from datetime import datetime, timezone
from config.extensions import db


class Connector(db.Model):
    """Connecteur MCP (Google Drive, Jira, Slack, Notion...)."""
    __tablename__ = 'connectors'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    type = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(db.DateTime, nullable=True)


class ConnectorCredentials(db.Model):
    """Credentials chiffrés d'un connecteur."""
    __tablename__ = 'connector_credentials'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    connector_id = db.Column(db.Uuid, db.ForeignKey('connectors.id'), nullable=False)
    encrypted_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(db.DateTime, nullable=True)


class ToolScope(db.Model):
    """Périmètre de données autorisé pour un connecteur."""
    __tablename__ = 'tool_scopes'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    connector_id = db.Column(db.Uuid, db.ForeignKey('connectors.id'), nullable=False)
    scope_type = db.Column(db.String, nullable=False)
    external_id = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    is_allowed = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(db.DateTime, nullable=True)
