"""Shared data models for all MCP connectors."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MCPResource:
    """A resource exposed by an MCP server (file, document, table row…)."""
    uri: str
    name: str
    description: str = ""
    mime_type: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class MCPTool:
    """A callable tool exposed by an MCP server."""
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPToolResult:
    """Result returned by an MCP tool call."""
    content: list = field(default_factory=list)
    is_error: bool = False

    def text(self) -> str:
        """Extract concatenated plain text from all content items."""
        return "\n".join(
            item.get("text", "")
            for item in self.content
            if item.get("type") == "text"
        )

    def to_dict(self) -> dict:
        return {"content": self.content, "is_error": self.is_error}


@dataclass
class ConnectorConfig:
    """Runtime configuration passed to an MCP client."""
    server_url: str
    auth_token: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class SyncResult:
    """Aggregated result of a full sync operation."""
    connector_id: str
    synced_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: list = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: str = "pending"  # pending | success | partial | failed

    def finish(self, status: str) -> None:
        self.finished_at = datetime.utcnow()
        self.status = status

    def to_dict(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "synced_count": self.synced_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
        }
