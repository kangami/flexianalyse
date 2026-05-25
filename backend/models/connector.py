from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional


@dataclass
class Connector:
    """Connecteur MCP (Google Drive, Jira, Slack, Notion...)."""
    id: UUID
    organization_id: UUID
    type: str         # google_drive, jira, slack, notion
    name: str
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "connectors"


@dataclass
class ConnectorCredentials:
    """Credentials chiffrés d'un connecteur."""
    id: UUID
    connector_id: UUID
    encrypted_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "connector_credentials"


@dataclass
class ToolScope:
    """Périmètre de données autorisé pour un connecteur."""
    id: UUID
    connector_id: UUID
    scope_type: str   # drive_folder, jira_project, slack_channel
    external_id: str  # folderId, projectKey, channelId
    name: str
    is_allowed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "tool_scopes"
