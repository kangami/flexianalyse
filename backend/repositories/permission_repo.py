from typing import Optional, List
from uuid import UUID
from models.permission import Permission, Policy, RolePermission
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

    def find_by_action_resource(self, action: str, resource: str) -> Optional[Permission]:
        row = self.db.fetch_one(
            "SELECT * FROM permissions WHERE action = %s AND resource = %s AND deleted_at IS NULL",
            (action, resource)
        )
        return Permission(**row) if row else None

    def list_by_role(self, role_id: UUID) -> List[Permission]:
        rows = self.db.fetch_all(
            """SELECT p.* FROM permissions p
               JOIN role_permissions rp ON rp.permission_id = p.id
               WHERE rp.role_id = %s AND p.deleted_at IS NULL
               AND now() BETWEEN p.valid_from AND p.valid_to
               ORDER BY p.resource, p.action""",
            (role_id,)
        )
        return [Permission(**r) for r in rows]

    def check_permission(self, role_id: UUID, action: str, resource: str) -> bool:
        row = self.db.fetch_one(
            """SELECT 1 FROM permissions p
               JOIN role_permissions rp ON rp.permission_id = p.id
               WHERE rp.role_id = %s AND p.action = %s AND p.resource = %s
               AND p.allowed = true AND p.deleted_at IS NULL
               AND now() BETWEEN p.valid_from AND p.valid_to
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
            """INSERT INTO permissions (action, resource, scope, allowed, valid_from, valid_to, version)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.action, entity.resource, entity.scope,
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


class RolePermissionRepository:
    """Accès à la table de jonction role_permissions."""

    def __init__(self, db_connection):
        self.db = db_connection

    def link(self, role_id: UUID, permission_id: UUID) -> bool:
        result = self.db.execute(
            "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (role_id, permission_id)
        )
        return result.rowcount > 0

    def unlink(self, role_id: UUID, permission_id: UUID) -> bool:
        result = self.db.execute(
            "DELETE FROM role_permissions WHERE role_id = %s AND permission_id = %s",
            (role_id, permission_id)
        )
        return result.rowcount > 0

    def list_by_role(self, role_id: UUID) -> List[RolePermission]:
        rows = self.db.fetch_all(
            "SELECT * FROM role_permissions WHERE role_id = %s", (role_id,)
        )
        return [RolePermission(**r) for r in rows]


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
