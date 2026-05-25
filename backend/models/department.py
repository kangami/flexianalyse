from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, Optional
from uuid import UUID


@dataclass
class Department:
    """Département au sein d'une organisation (IT, Sales, RH...)."""
    TABLE: ClassVar[str] = "departments"

    id: UUID
    organization_id: UUID
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None  # Soft delete
