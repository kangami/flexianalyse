from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class Organization:
    """ Organisation — tenant racine du multi-tenant."""
    id: UUID
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "organizations"
