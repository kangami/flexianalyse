from typing import Optional, List
from uuid import UUID
from models.rate_limit import RateLimit
from .base import BaseRepository


class RateLimitRepository(BaseRepository[RateLimit]):
    """Accès aux données de la table rate_limits."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[RateLimit]:
        row = self.db.fetch_one(
            "SELECT * FROM rate_limits WHERE id = %s", (id,)
        )
        return RateLimit(**row) if row else None

    def get_for_org_connector(self, organization_id: UUID, connector_type: str) -> Optional[RateLimit]:
        row = self.db.fetch_one(
            "SELECT * FROM rate_limits WHERE organization_id = %s AND connector_type = %s",
            (organization_id, connector_type)
        )
        return RateLimit(**row) if row else None

    def list_by_organization(self, organization_id: UUID) -> List[RateLimit]:
        rows = self.db.fetch_all(
            "SELECT * FROM rate_limits WHERE organization_id = %s ORDER BY connector_type",
            (organization_id,)
        )
        return [RateLimit(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[RateLimit]:
        rows = self.db.fetch_all(
            "SELECT * FROM rate_limits ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [RateLimit(**r) for r in rows]

    def create(self, entity: RateLimit) -> RateLimit:
        row = self.db.fetch_one(
            """INSERT INTO rate_limits (organization_id, connector_type, max_requests, window_seconds, current_count, reset_at)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.connector_type, entity.max_requests,
             entity.window_seconds, entity.current_count, entity.reset_at)
        )
        return RateLimit(**row)

    def increment_and_check(self, organization_id: UUID, connector_type: str) -> bool:
        """Incrémente le compteur et retourne True si sous la limite."""
        row = self.db.fetch_one(
            """UPDATE rate_limits
               SET current_count = CASE
                   WHEN reset_at IS NULL OR reset_at <= now() THEN 1
                   ELSE current_count + 1
               END,
               reset_at = CASE
                   WHEN reset_at IS NULL OR reset_at <= now() THEN now() + (window_seconds * interval '1 second')
                   ELSE reset_at
               END,
               updated_at = now()
               WHERE organization_id = %s AND connector_type = %s
               RETURNING current_count <= max_requests AS allowed""",
            (organization_id, connector_type)
        )
        return row["allowed"] if row else False

    def update(self, entity: RateLimit) -> RateLimit:
        row = self.db.fetch_one(
            """UPDATE rate_limits SET max_requests = %s, window_seconds = %s, updated_at = now()
               WHERE id = %s RETURNING *""",
            (entity.max_requests, entity.window_seconds, entity.id)
        )
        return RateLimit(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM rate_limits WHERE id = %s", (id,))
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM rate_limits WHERE id = %s", (id,))
        return result.rowcount > 0
