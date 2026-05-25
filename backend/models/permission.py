from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID
from typing import Optional, Any


class Action(StrEnum):
    READ    = "read"
    WRITE   = "write"
    EXECUTE = "execute"
    DELETE  = "delete"


class Resource(StrEnum):
    CHAT         = "chat"
    AGENT        = "agent"
    CONNECTOR    = "connector"
    REPORTING    = "reporting"
    ORGANISATION = "organisation"


@dataclass
class Permission:
    """Permission IAM-style avec versioning temporel."""
    id: UUID
    role_id: UUID
    action: Action
    resource: Resource
    scope: str        # org, project, folder
    allowed: bool = True
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_to: datetime = field(default_factory=lambda: datetime.max)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "permissions"


@dataclass
class Policy:
    """Policy engine avancé avec conditions JSONB et priorité."""
    id: UUID
    organization_id: UUID
    name: str
    effect: str       # allow / deny
    condition: dict = field(default_factory=dict)  # JSONB
    priority: int = 0
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_to: datetime = field(default_factory=lambda: datetime.max)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "policies"
