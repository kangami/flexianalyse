from typing import Optional, List
from uuid import UUID
from models.connector import Connector, ConnectorCredentials, ToolScope
from .base import BaseRepository


class ConnectorRepository(BaseRepository[Connector]):
    """Accès aux données de la table connectors."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Connector]:
        row = self.db.fetch_one(
            "SELECT * FROM connectors WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Connector(**row) if row else None

    def list_by_organization(self, organization_id: UUID) -> List[Connector]:
        rows = self.db.fetch_all(
            "SELECT * FROM connectors WHERE organization_id = %s AND deleted_at IS NULL ORDER BY created_at DESC",
            (organization_id,)
        )
        return [Connector(**r) for r in rows]

    def list_active_by_organization(self, organization_id: UUID) -> List[Connector]:
        rows = self.db.fetch_all(
            "SELECT * FROM connectors WHERE organization_id = %s AND status = 'active' AND deleted_at IS NULL",
            (organization_id,)
        )
        return [Connector(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Connector]:
        rows = self.db.fetch_all(
            "SELECT * FROM connectors WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Connector(**r) for r in rows]

    def create(self, entity: Connector) -> Connector:
        row = self.db.fetch_one(
            """INSERT INTO connectors (organization_id, type, name, status) VALUES (%s, %s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.type, entity.name, entity.status)
        )
        return Connector(**row)

    def update(self, entity: Connector) -> Connector:
        row = self.db.fetch_one(
            """UPDATE connectors SET name = %s, status = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.status, entity.id)
        )
        return Connector(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE connectors SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM connectors WHERE id = %s", (id,))
        return result.rowcount > 0


class ConnectorCredentialsRepository(BaseRepository[ConnectorCredentials]):
    """Accès aux données de la table connector_credentials."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[ConnectorCredentials]:
        row = self.db.fetch_one(
            "SELECT * FROM connector_credentials WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return ConnectorCredentials(**row) if row else None

    def get_by_connector(self, connector_id: UUID) -> Optional[ConnectorCredentials]:
        row = self.db.fetch_one(
            "SELECT * FROM connector_credentials WHERE connector_id = %s AND deleted_at IS NULL",
            (connector_id,)
        )
        return ConnectorCredentials(**row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ConnectorCredentials]:
        rows = self.db.fetch_all(
            "SELECT * FROM connector_credentials WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [ConnectorCredentials(**r) for r in rows]

    def create(self, entity: ConnectorCredentials) -> ConnectorCredentials:
        row = self.db.fetch_one(
            """INSERT INTO connector_credentials (connector_id, encrypted_token, refresh_token, expires_at)
               VALUES (%s, %s, %s, %s) RETURNING *""",
            (entity.connector_id, entity.encrypted_token, entity.refresh_token, entity.expires_at)
        )
        return ConnectorCredentials(**row)

    def update(self, entity: ConnectorCredentials) -> ConnectorCredentials:
        row = self.db.fetch_one(
            """UPDATE connector_credentials SET encrypted_token = %s, refresh_token = %s,
               expires_at = %s, updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.encrypted_token, entity.refresh_token, entity.expires_at, entity.id)
        )
        return ConnectorCredentials(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE connector_credentials SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM connector_credentials WHERE id = %s", (id,))
        return result.rowcount > 0


class ToolScopeRepository(BaseRepository[ToolScope]):
    """Accès aux données de la table tool_scopes."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[ToolScope]:
        row = self.db.fetch_one(
            "SELECT * FROM tool_scopes WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return ToolScope(**row) if row else None

    def list_by_connector(self, connector_id: UUID) -> List[ToolScope]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_scopes WHERE connector_id = %s AND deleted_at IS NULL ORDER BY scope_type, name",
            (connector_id,)
        )
        return [ToolScope(**r) for r in rows]

    def list_allowed_by_connector(self, connector_id: UUID) -> List[ToolScope]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_scopes WHERE connector_id = %s AND is_allowed = true AND deleted_at IS NULL",
            (connector_id,)
        )
        return [ToolScope(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolScope]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_scopes WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [ToolScope(**r) for r in rows]

    def create(self, entity: ToolScope) -> ToolScope:
        row = self.db.fetch_one(
            """INSERT INTO tool_scopes (connector_id, scope_type, external_id, name, is_allowed)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (entity.connector_id, entity.scope_type, entity.external_id, entity.name, entity.is_allowed)
        )
        return ToolScope(**row)

    def update(self, entity: ToolScope) -> ToolScope:
        row = self.db.fetch_one(
            """UPDATE tool_scopes SET name = %s, is_allowed = %s
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.is_allowed, entity.id)
        )
        return ToolScope(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE tool_scopes SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM tool_scopes WHERE id = %s", (id,))
        return result.rowcount > 0
