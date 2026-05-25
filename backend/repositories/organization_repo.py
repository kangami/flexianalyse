from typing import Optional, List
from uuid import UUID
from models.organization import Organization
from .base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Accès aux données de la table organizations."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Organization]:
        row = self.db.fetch_one(
            "SELECT * FROM organizations WHERE id = %s AND deleted_at IS NULL",
            (id,)
        )
        return Organization(**row) if row else None

    def get_by_name(self, name: str) -> Optional[Organization]:
        row = self.db.fetch_one(
            "SELECT * FROM organizations WHERE LOWER(name) = LOWER(%s) AND deleted_at IS NULL",
            (name,)
        )
        return Organization(**row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Organization]:
        rows = self.db.fetch_all(
            "SELECT * FROM organizations WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Organization(**r) for r in rows]

    def create(self, entity: Organization) -> Organization:
        row = self.db.fetch_one(
            """INSERT INTO organizations (name) VALUES (%s) RETURNING *""",
            (entity.name,)
        )
        return Organization(**row)

    def update(self, entity: Organization) -> Organization:
        row = self.db.fetch_one(
            """UPDATE organizations SET name = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.name, entity.id)
        )
        return Organization(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE organizations SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL",
            (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "DELETE FROM organizations WHERE id = %s",
            (id,)
        )
        return result.rowcount > 0
