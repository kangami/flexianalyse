from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models.audit_log import AuditLog
from .base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Accès aux données de la table audit_logs (partitionnée)."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[AuditLog]:
        row = self.db.fetch_one(
            "SELECT * FROM audit_logs WHERE id = %s", (id,)
        )
        return AuditLog(**row) if row else None

    def list_by_organization(self, organization_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_logs WHERE organization_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (organization_id, limit, offset)
        )
        return [AuditLog(**r) for r in rows]

    def list_by_user(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_logs WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (user_id, limit, offset)
        )
        return [AuditLog(**r) for r in rows]

    def list_by_action(self, organization_id: UUID, action: str, limit: int = 100) -> List[AuditLog]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_logs WHERE organization_id = %s AND action = %s ORDER BY created_at DESC LIMIT %s",
            (organization_id, action, limit)
        )
        return [AuditLog(**r) for r in rows]

    def list_by_date_range(self, organization_id: UUID, start: datetime, end: datetime, limit: int = 500) -> List[AuditLog]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_logs WHERE organization_id = %s AND created_at BETWEEN %s AND %s ORDER BY created_at DESC LIMIT %s",
            (organization_id, start, end, limit)
        )
        return [AuditLog(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        rows = self.db.fetch_all(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [AuditLog(**r) for r in rows]

    def create(self, entity: AuditLog) -> AuditLog:
        row = self.db.fetch_one(
            """INSERT INTO audit_logs (organization_id, user_id, action, resource, tool, metadata)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.user_id, entity.action,
             entity.resource, entity.tool, entity.metadata)
        )
        return AuditLog(**row)

    def update(self, entity: AuditLog) -> AuditLog:
        raise NotImplementedError("Audit logs are append-only")

    def soft_delete(self, id: UUID) -> bool:
        raise NotImplementedError("Audit logs are append-only — use retention policies instead")

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM audit_logs WHERE id = %s", (id,))
        return result.rowcount > 0
