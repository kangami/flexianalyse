from typing import Optional, List
from uuid import UUID
from models.role import Role, Membership
from .base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Accès aux données de la table roles."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Role]:
        row = self.db.fetch_one(
            "SELECT * FROM roles WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Role(**row) if row else None

    def list_by_organization(self, organization_id: UUID) -> List[Role]:
        rows = self.db.fetch_all(
            "SELECT * FROM roles WHERE organization_id = %s AND deleted_at IS NULL ORDER BY name",
            (organization_id,)
        )
        return [Role(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Role]:
        rows = self.db.fetch_all(
            "SELECT * FROM roles WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Role(**r) for r in rows]

    def create(self, entity: Role) -> Role:
        row = self.db.fetch_one(
            """INSERT INTO roles (organization_id, name, is_system) VALUES (%s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.name, entity.is_system)
        )
        return Role(**row)

    def update(self, entity: Role) -> Role:
        row = self.db.fetch_one(
            """UPDATE roles SET name = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.id)
        )
        return Role(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE roles SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM roles WHERE id = %s", (id,))
        return result.rowcount > 0


class MembershipRepository(BaseRepository[Membership]):
    """Accès aux données de la table memberships."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Membership]:
        row = self.db.fetch_one(
            "SELECT * FROM memberships WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Membership(**row) if row else None

    def get_active_for_user_org(self, user_id: UUID, organization_id: UUID) -> Optional[Membership]:
        row = self.db.fetch_one(
            """SELECT * FROM memberships
               WHERE user_id = %s AND organization_id = %s AND status = 'active' AND deleted_at IS NULL""",
            (user_id, organization_id)
        )
        return Membership(**row) if row else None

    def list_by_user(self, user_id: UUID) -> List[Membership]:
        rows = self.db.fetch_all(
            "SELECT * FROM memberships WHERE user_id = %s AND deleted_at IS NULL ORDER BY created_at DESC",
            (user_id,)
        )
        return [Membership(**r) for r in rows]

    def list_by_organization(self, organization_id: UUID) -> List[Membership]:
        rows = self.db.fetch_all(
            "SELECT * FROM memberships WHERE organization_id = %s AND deleted_at IS NULL ORDER BY created_at DESC",
            (organization_id,)
        )
        return [Membership(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Membership]:
        rows = self.db.fetch_all(
            "SELECT * FROM memberships WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Membership(**r) for r in rows]

    def create(self, entity: Membership) -> Membership:
        row = self.db.fetch_one(
            """INSERT INTO memberships (user_id, organization_id, role_id, status)
               VALUES (%s, %s, %s, %s) RETURNING *""",
            (entity.user_id, entity.organization_id, entity.role_id, entity.status)
        )
        return Membership(**row)

    def update(self, entity: Membership) -> Membership:
        row = self.db.fetch_one(
            """UPDATE memberships SET role_id = %s, status = %s
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.role_id, entity.status, entity.id)
        )
        return Membership(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE memberships SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM memberships WHERE id = %s", (id,))
        return result.rowcount > 0
