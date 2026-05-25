from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class User:
    """Utilisateur de la plateforme."""
    id: UUID
    email: str
    password_hash: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "users"


@dataclass
class UserSession:
    """🔐 Session utilisateur (refresh token)."""
    id: UUID
    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None  # INET in PG
    created_at: datetime = field(default_factory=datetime.utcnow)

    TABLE = "user_sessions"
