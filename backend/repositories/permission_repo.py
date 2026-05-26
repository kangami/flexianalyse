from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.permission import Permission, Policy, RolePermission
from .base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    """Accès aux données de la table permissions (IAM)."""

    def get_by_id(self, id: UUID) -> Optional[Permission]:
        return db.session.scalars(
            select(Permission).where(Permission.id == id, Permission.deleted_at.is_(None))
        ).first()

    def find_by_action_resource(self, action: str, resource: str) -> Optional[Permission]:
        return db.session.scalars(
            select(Permission)
            .where(Permission.action == action, Permission.resource == resource, Permission.deleted_at.is_(None))
        ).first()

    def list_by_role(self, role_id: UUID) -> List[Permission]:
        return list(db.session.scalars(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id, Permission.deleted_at.is_(None))
            .order_by(Permission.resource, Permission.action)
        ).all())

    def check_permission(self, role_id: UUID, action: str, resource: str) -> bool:
        result = db.session.scalars(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == role_id,
                Permission.action == action,
                Permission.resource == resource,
                Permission.allowed.is_(True),
                Permission.deleted_at.is_(None),
            )
            .limit(1)
        ).first()
        return result is not None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Permission]:
        return list(db.session.scalars(
            select(Permission).where(Permission.deleted_at.is_(None))
            .order_by(Permission.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Permission) -> Permission:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Permission) -> Permission:
        entity.version = (entity.version or 1) + 1
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Permission).where(Permission.id == id, Permission.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Permission, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class RolePermissionRepository:
    """Accès à la table de jonction role_permissions."""

    def link(self, role_id: UUID, permission_id: UUID) -> bool:
        existing = db.session.get(RolePermission, (role_id, permission_id))
        if existing:
            return False
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        db.session.add(rp)
        db.session.commit()
        return True

    def unlink(self, role_id: UUID, permission_id: UUID) -> bool:
        entity = db.session.get(RolePermission, (role_id, permission_id))
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True

    def list_by_role(self, role_id: UUID) -> List[RolePermission]:
        return list(db.session.scalars(
            select(RolePermission).where(RolePermission.role_id == role_id)
        ).all())


class PolicyRepository(BaseRepository[Policy]):
    """Accès aux données de la table policies (Policy Engine)."""

    def get_by_id(self, id: UUID) -> Optional[Policy]:
        return db.session.scalars(
            select(Policy).where(Policy.id == id, Policy.deleted_at.is_(None))
        ).first()

    def list_by_organization(self, organization_id: UUID) -> List[Policy]:
        return list(db.session.scalars(
            select(Policy)
            .where(Policy.organization_id == organization_id, Policy.deleted_at.is_(None))
            .order_by(Policy.priority.desc())
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Policy]:
        return list(db.session.scalars(
            select(Policy).where(Policy.deleted_at.is_(None))
            .order_by(Policy.priority.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Policy) -> Policy:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Policy) -> Policy:
        entity.version = (entity.version or 1) + 1
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Policy).where(Policy.id == id, Policy.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Policy, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
