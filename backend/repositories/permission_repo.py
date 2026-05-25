from typing import Optional, List
from uuid import UUID
from models.permission import Permission, Policy
from .base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    """Accès aux données de la table permissions (IAM)."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Permission]:
        row = self.db.fetch_one(
            "SELECT * FROM permissions WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Permission(**row) if row else None

    def list_by_role(self, role_id: UUID) -> List[Permission]:
        rows = self.db.fetch_all(
            """SELECT * FROM permissions
               WHERE role_id = %s AND deleted_at IS NULL
               AND now() BETWEEN valid_from AND valid_to
               ORDER BY resource, action""",
            (role_id,)
        )
        return [Permission(**r) for r in rows]

    def check_permission(self, role_id: UUID, action: str, resource: str) -> bool:
        row = self.db.fetch_one(
            """SELECT 1 FROM permissions
               WHERE role_id = %s AND action = %s AND resource = %s
               AND allowed = true AND deleted_at IS NULL
               AND now() BETWEEN valid_from AND valid_to
               LIMIT 1""",
            (role_id, action, resource)
        )
        return row is not None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Permission]:
        rows = self.db.fetch_all(
            "SELECT * FROM permissions WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Permission(**r) for r in rows]

    def create(self, entity: Permission) -> Permission:
        row = self.db.fetch_one(
            """INSERT INTO permissions (role_id, action, resource, scope, allowed, valid_from, valid_to, version)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.role_id, entity.action, entity.resource, entity.scope,
             entity.allowed, entity.valid_from, entity.valid_to, entity.version)
        )
        return Permission(**row)

    def update(self, entity: Permission) -> Permission:
        row = self.db.fetch_one(
            """UPDATE permissions SET action = %s, resource = %s, scope = %s, allowed = %s,
               valid_from = %s, valid_to = %s, version = version + 1
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.action, entity.resource, entity.scope, entity.allowed,
             entity.valid_from, entity.valid_to, entity.id)
        )
        return Permission(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE permissions SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM permissions WHERE id = %s", (id,))
        return result.rowcount > 0


class PolicyRepository(BaseRepository[Policy]):
    """Accès aux données de la table policies (Policy Engine)."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Policy]:
        row = self.db.fetch_one(
            "SELECT * FROM policies WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Policy(**row) if row else None

    def list_by_organization(self, organization_id: UUID) -> List[Policy]:
        rows = self.db.fetch_all(
            """SELECT * FROM policies
               WHERE organization_id = %s AND deleted_at IS NULL
               AND now() BETWEEN valid_from AND valid_to
               ORDER BY priority DESC""",
            (organization_id,)
        )
        return [Policy(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Policy]:
        rows = self.db.fetch_all(
            "SELECT * FROM policies WHERE deleted_at IS NULL ORDER BY priority DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Policy(**r) for r in rows]

    def create(self, entity: Policy) -> Policy:
        row = self.db.fetch_one(
            """INSERT INTO policies (organization_id, name, effect, condition, priority, valid_from, valid_to, version)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.name, entity.effect, entity.condition,
             entity.priority, entity.valid_from, entity.valid_to, entity.version)
        )
        return Policy(**row)

    def update(self, entity: Policy) -> Policy:
        row = self.db.fetch_one(
            """UPDATE policies SET name = %s, effect = %s, condition = %s, priority = %s,
               valid_from = %s, valid_to = %s, version = version + 1
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.effect, entity.condition, entity.priority,
             entity.valid_from, entity.valid_to, entity.id)
        )
        return Policy(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE policies SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM policies WHERE id = %s", (id,))
        return result.rowcount > 0
