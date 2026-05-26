from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from config.extensions import db
from models.audit_log import AuditLog
from .base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Accès aux données de la table audit_logs."""

    def get_by_id(self, id: UUID) -> Optional[AuditLog]:
        return db.session.get(AuditLog, id)

    def list_by_organization(self, organization_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        return list(db.session.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def list_by_user(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        return list(db.session.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def list_by_action(self, organization_id: UUID, action: str, limit: int = 100) -> List[AuditLog]:
        return list(db.session.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id, AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).all())

    def list_by_date_range(self, organization_id: UUID, start: datetime, end: datetime, limit: int = 500) -> List[AuditLog]:
        return list(db.session.scalars(
            select(AuditLog)
            .where(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at >= start,
                AuditLog.created_at <= end,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        return list(db.session.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: AuditLog) -> AuditLog:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: AuditLog) -> AuditLog:
        raise NotImplementedError("Audit logs are append-only")

    def soft_delete(self, id: UUID) -> bool:
        raise NotImplementedError("Audit logs are append-only — use retention policies instead")

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(AuditLog, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
