from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class RateLimit:
    """🚦 Rate limiting par organisation et type de connecteur."""
    id: UUID
    organization_id: UUID
    connector_type: str       # google_drive, jira
    max_requests: int = 100
    window_seconds: int = 60
    current_count: int = 0
    reset_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    TABLE = "rate_limits"
