from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from enum import StrEnum
from typing import ClassVar, Optional, Any


class AuditAction(StrEnum):
    CREATE = "create"
    READ   = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN  = "login"
    DENIED = "denied"


@dataclass
class AuditLog:
    """Log d'audit (table partitionnée par année)."""
    TABLE: ClassVar[str] = "audit_logs"
    
    id: UUID
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    resource: Optional[str] = None
    tool: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # JSONB
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
