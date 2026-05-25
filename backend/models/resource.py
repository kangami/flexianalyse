from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


@dataclass
class Resource:
    """Ressource unifiée (fichier, ticket, message, doc...)."""
    id: UUID
    organization_id: UUID
    connector_id: Optional[UUID] = None
    external_id: Optional[str] = None
    type: Optional[str] = None   # file, ticket, message, doc
    title: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # JSONB
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete
    search_vector: Optional[Any] = None    # TSVECTOR (PG interne)

    TABLE = "resources"


@dataclass
class ResourceBinding:
    """Binding sécurité entre ressource et périmètre outil."""
    id: UUID
    resource_id: UUID
    tool_scope_id: UUID
    access_level: str  # read, write
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "resource_bindings"
