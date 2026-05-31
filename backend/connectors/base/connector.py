"""Base classes shared by all MCP connector implementations."""
import logging
from abc import ABC, abstractmethod

import requests

from .models import ConnectorConfig, MCPResource, MCPTool, MCPToolResult, SyncResult

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Raised when an MCP server returns a JSON-RPC error."""
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class MCPTransport:
    """
    Minimal JSON-RPC 2.0 transport over HTTP for the Model Context Protocol.

    Each concrete mcp_client.py inherits from this class and adds
    connector-specific convenience methods.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.server_url = config.server_url.rstrip("/")
        self._request_id = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.config.auth_token:
            h["Authorization"] = f"Bearer {self.config.auth_token}"
        return h

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        try:
            resp = requests.post(
                self.server_url,
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise MCPError(f"Transport error: {exc}") from exc

        data = resp.json()
        if "error" in data:
            raise MCPError(data["error"].get("message", "MCP error"), data["error"].get("code"))
        return data.get("result", {})

    # ------------------------------------------------------------------
    # MCP protocol methods
    # ------------------------------------------------------------------

    def initialize(self) -> dict:
        return self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "flexianalyse-connector", "version": "1.0.0"},
        })

    def list_tools(self) -> list[MCPTool]:
        result = self._rpc("tools/list")
        return [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in result.get("tools", [])
        ]

    def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return MCPToolResult(
            content=result.get("content", []),
            is_error=result.get("isError", False),
        )

    def list_resources(self) -> list[MCPResource]:
        result = self._rpc("resources/list")
        return [
            MCPResource(
                uri=r["uri"],
                name=r.get("name", ""),
                description=r.get("description", ""),
                mime_type=r.get("mimeType"),
            )
            for r in result.get("resources", [])
        ]

    def read_resource(self, uri: str) -> str:
        result = self._rpc("resources/read", {"uri": uri})
        parts = []
        for item in result.get("contents", []):
            if "text" in item:
                parts.append(item["text"])
            elif "blob" in item:
                parts.append(f"[binary: {item.get('uri', uri)}]")
        return "\n".join(parts)


class BaseConnector(ABC):
    """
    Abstract interface every connector provider must implement.

    Concrete connectors compose a connector-specific MCPTransport subclass
    (mcp_client.py) with business logic (service.py) and sync logic (sync.py).
    """

    connector_type: str = "base"

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config

    @abstractmethod
    def list_tools(self) -> list[MCPTool]:
        """Return all tools the MCP server exposes."""

    @abstractmethod
    def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        """Invoke a named tool with the given arguments."""

    @abstractmethod
    def list_resources(self) -> list[MCPResource]:
        """Return all resources available on the MCP server."""

    @abstractmethod
    def read_resource(self, uri: str) -> str:
        """Fetch the raw content of the resource identified by *uri*."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the MCP server is reachable and credentials are valid."""

    @abstractmethod
    def sync(self, connector_id: str) -> SyncResult:
        """Synchronise remote resources into the local database."""
