from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.rate_limit import RateLimit
from .base import BaseRepository


class RateLimitRepository(BaseRepository[RateLimit]):
    """Accès aux données de la table rate_limits."""

    def get_by_id(self, id: UUID) -> Optional[RateLimit]:
        return db.session.get(RateLimit, id)

    def get_for_org_connector(self, organization_id: UUID, connector_type: str) -> Optional[RateLimit]:
        return db.session.scalars(
            select(RateLimit)
            .where(RateLimit.organization_id == organization_id, RateLimit.connector_type == connector_type)
        ).first()

    def list_by_organization(self, organization_id: UUID) -> List[RateLimit]:
        return list(db.session.scalars(
            select(RateLimit)
            .where(RateLimit.organization_id == organization_id)
            .order_by(RateLimit.connector_type)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[RateLimit]:
        return list(db.session.scalars(
            select(RateLimit)
            .order_by(RateLimit.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: RateLimit) -> RateLimit:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def increment_and_check(self, organization_id: UUID, connector_type: str) -> bool:
        """Incrémente le compteur et retourne True si sous la limite."""
        rl = self.get_for_org_connector(organization_id, connector_type)
        if not rl:
            return False
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if rl.reset_at is None or rl.reset_at <= now:
            rl.current_count = 1
            rl.reset_at = now + timedelta(seconds=rl.window_seconds)
        else:
            rl.current_count += 1
        rl.updated_at = now
        db.session.commit()
        return rl.current_count <= rl.max_requests

    def update(self, entity: RateLimit) -> RateLimit:
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        return self.hard_delete(id)

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(RateLimit, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
