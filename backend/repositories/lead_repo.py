from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.lead import Lead
from .base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Accès aux données de la table leads."""

    def get_by_id(self, id: UUID) -> Optional[Lead]:
        return db.session.get(Lead, id)

    def get_by_email(self, email: str) -> Optional[Lead]:
        return db.session.scalars(
            select(Lead).where(Lead.work_email == email)
        ).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Lead]:
        return list(db.session.scalars(
            select(Lead)
            .order_by(Lead.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Lead) -> Lead:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Lead) -> Lead:
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.get(Lead, id)
        if not entity:
            return False
        entity.status = 'deleted'
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Lead, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
