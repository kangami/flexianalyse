from typing import Optional, List
from uuid import UUID
from models.department import Department
from .base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    """Accès aux données de la table departments."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Department]:
        row = self.db.fetch_one(
            "SELECT * FROM departments WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Department(**row) if row else None

    def get_by_name_in_org(self, organization_id: UUID, name: str, exclude_id: UUID = None) -> Optional[Department]:
        if exclude_id:
            row = self.db.fetch_one(
                "SELECT * FROM departments WHERE organization_id = %s AND LOWER(name) = LOWER(%s) AND deleted_at IS NULL AND id != %s",
                (organization_id, name, exclude_id)
            )
        else:
            row = self.db.fetch_one(
                "SELECT * FROM departments WHERE organization_id = %s AND LOWER(name) = LOWER(%s) AND deleted_at IS NULL",
                (organization_id, name)
            )
        return Department(**row) if row else None

    def list_by_organization(self, organization_id: UUID) -> List[Department]:
        rows = self.db.fetch_all(
            "SELECT * FROM departments WHERE organization_id = %s AND deleted_at IS NULL ORDER BY name",
            (organization_id,)
        )
        return [Department(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Department]:
        rows = self.db.fetch_all(
            "SELECT * FROM departments WHERE deleted_at IS NULL ORDER BY name LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Department(**r) for r in rows]

    def create(self, entity: Department) -> Department:
        row = self.db.fetch_one(
            """INSERT INTO departments (organization_id, name) VALUES (%s, %s) RETURNING *""",
            (entity.organization_id, entity.name)
        )
        return Department(**row)

    def update(self, entity: Department) -> Department:
        row = self.db.fetch_one(
            """UPDATE departments SET name = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.id)
        )
        return Department(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE departments SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM departments WHERE id = %s", (id,))
        return result.rowcount > 0
