from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from config.extensions import db
from models.department import Department
from .base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    """Accès aux données de la table departments."""

    def get_by_id(self, id: UUID) -> Optional[Department]:
        return db.session.scalars(
            select(Department)
            .where(Department.id == id, Department.deleted_at.is_(None))
        ).first()

    def get_by_name_in_org(self, organization_id: UUID, name: str, exclude_id: UUID = None) -> Optional[Department]:
        stmt = (
            select(Department)
            .where(
                Department.organization_id == organization_id,
                func.lower(Department.name) == name.lower(),
                Department.deleted_at.is_(None),
            )
        )
        if exclude_id:
            stmt = stmt.where(Department.id != exclude_id)
        return db.session.scalars(stmt).first()

    def list_by_organization(self, organization_id: UUID) -> List[Department]:
        return list(db.session.scalars(
            select(Department)
            .where(Department.organization_id == organization_id, Department.deleted_at.is_(None))
            .order_by(Department.name)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Department]:
        return list(db.session.scalars(
            select(Department)
            .where(Department.deleted_at.is_(None))
            .order_by(Department.name)
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Department) -> Department:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Department) -> Department:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Department).where(Department.id == id, Department.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Department, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
