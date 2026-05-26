from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from config.extensions import db
from models.organization import Organization
from .base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Accès aux données de la table organizations."""

    def get_by_id(self, id: UUID) -> Optional[Organization]:
        return db.session.scalars(
            select(Organization)
            .where(Organization.id == id, Organization.deleted_at.is_(None))
        ).first()

    def get_by_name(self, name: str) -> Optional[Organization]:
        return db.session.scalars(
            select(Organization)
            .where(func.lower(Organization.name) == name.lower(), Organization.deleted_at.is_(None))
        ).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Organization]:
        return list(db.session.scalars(
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Organization) -> Organization:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Organization) -> Organization:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Organization).where(Organization.id == id, Organization.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Organization, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
