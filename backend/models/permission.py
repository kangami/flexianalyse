from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID
from typing import Optional, Any


class Action(StrEnum):
    READ      = "read"
    CREATE    = "create"
    UPDATE    = "update"
    DELETE    = "delete"
    ASSIGN    = "assign"
    EXECUTE   = "execute"
    MANAGE    = "manage"
    EXPORT    = "export"
    SYNC      = "sync"
    AUTHORIZE = "authorize"


class Resource(StrEnum):
    ORGANIZATIONS = "organizations"
    USERS         = "users"
    MEMBERSHIPS   = "memberships"
    DEPARTMENTS   = "departments"
    TEAMS         = "teams"
    ROLES         = "roles"
    PERMISSIONS   = "permissions"
    CONNECTORS    = "connectors"
    DOCUMENTS     = "documents"
    CASES         = "cases"
    ANALYSES      = "analyses"
    PROMPTS       = "prompts"
    AI_AGENTS     = "ai_agents"
    AUDIT_LOGS    = "audit_logs"
    SETTINGS      = "settings"
    BILLING       = "billing"


@dataclass
class Permission:
    """Permission IAM-style avec versioning temporel."""
    id: UUID
    action: Action
    resource: Resource
    scope: str = "org"
    allowed: bool = True
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_to: datetime = field(default_factory=lambda: datetime.max)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "permissions"


@dataclass
class RolePermission:
    """Junction many-to-many entre rôles et permissions."""
    role_id: UUID
    permission_id: UUID
    created_at: datetime = field(default_factory=datetime.utcnow)

    TABLE = "role_permissions"


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
