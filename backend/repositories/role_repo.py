from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.role import Role, Membership
from .base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Accès aux données de la table roles."""

    def get_by_id(self, id: UUID) -> Optional[Role]:
        return db.session.scalars(
            select(Role).where(Role.id == id, Role.deleted_at.is_(None))
        ).first()

    def list_by_organization(self, organization_id: UUID) -> List[Role]:
        return list(db.session.scalars(
            select(Role)
            .where(Role.organization_id == organization_id, Role.deleted_at.is_(None))
            .order_by(Role.name)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Role]:
        return list(db.session.scalars(
            select(Role).where(Role.deleted_at.is_(None))
            .order_by(Role.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Role) -> Role:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Role) -> Role:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Role).where(Role.id == id, Role.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Role, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class MembershipRepository(BaseRepository[Membership]):
    """Accès aux données de la table memberships."""

    def get_by_id(self, id: UUID) -> Optional[Membership]:
        return db.session.scalars(
            select(Membership).where(Membership.id == id, Membership.deleted_at.is_(None))
        ).first()

    def get_active_for_user_org(self, user_id: UUID, organization_id: UUID) -> Optional[Membership]:
        return db.session.scalars(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == organization_id,
                Membership.status == 'active',
                Membership.deleted_at.is_(None),
            )
        ).first()

    def list_by_user(self, user_id: UUID) -> List[Membership]:
        return list(db.session.scalars(
            select(Membership)
            .where(Membership.user_id == user_id, Membership.deleted_at.is_(None))
            .order_by(Membership.created_at.desc())
        ).all())

    def list_by_organization(self, organization_id: UUID) -> List[Membership]:
        return list(db.session.scalars(
            select(Membership)
            .where(Membership.organization_id == organization_id, Membership.deleted_at.is_(None))
            .order_by(Membership.created_at.desc())
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Membership]:
        return list(db.session.scalars(
            select(Membership).where(Membership.deleted_at.is_(None))
            .order_by(Membership.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Membership) -> Membership:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Membership) -> Membership:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Membership).where(Membership.id == id, Membership.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Membership, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
