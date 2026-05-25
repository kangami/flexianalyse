from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


@dataclass
class Conversation:
    """ Conversation AI."""
    id: UUID
    organization_id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "conversations"


@dataclass
class Message:
    """ Message dans une conversation (user / assistant / tool)."""
    id: UUID
    conversation_id: UUID
    role: str          # user, assistant, tool
    content: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    search_vector: Optional[Any] = None  # TSVECTOR (PG interne)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "messages"


@dataclass
class ToolCall:
    """🔧 Appel d'outil MCP tracé."""
    id: UUID
    message_id: UUID
    connector_id: Optional[UUID] = None
    tool_name: Optional[str] = None
    input: dict = field(default_factory=dict)    # JSONB
    output: dict = field(default_factory=dict)   # JSONB
    status: Optional[str] = None  # success, denied, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None  # Soft delete

    TABLE = "tool_calls"


@dataclass
class ToolApproval:
    """✅ Workflow d'approbation d'un appel d'outil."""
    id: UUID
    tool_call_id: UUID
    approver_user_id: Optional[UUID] = None
    status: str = "pending"  # pending, approved, denied
    justification: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    TABLE = "tool_approvals"
