from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class Role:
    """Rôle au sein d'une organisation (admin, member, external...)."""
    id: UUID
    organization_id: UUID
    name: str
    is_system: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "roles"


@dataclass
class Membership:
    """Lien user ↔ organisation avec un rôle (multi-tenant)."""
    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: Optional[UUID] = None
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "memberships"
