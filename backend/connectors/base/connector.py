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

    def _get(self, path: str) -> dict:
        """GET request to the MCP server REST API."""
        try:
            resp = requests.get(
                f"{self.server_url}{path}",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise MCPError(f"Transport error: {exc}") from exc
        return resp.json()

    def _post(self, path: str, body: dict | None = None, params: dict | None = None) -> dict:
        """POST request to the MCP server REST API."""
        try:
            resp = requests.post(
                f"{self.server_url}{path}",
                json=body or {},
                params=params,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise MCPError(f"Transport error: {exc}") from exc
        return resp.json()

    # ------------------------------------------------------------------
    # MCP protocol methods  (REST API: /health, /tools, /execute)
    # ------------------------------------------------------------------

    def initialize(self) -> dict:
        """Verify the server is reachable via GET /health."""
        return self._get("/health")

    def list_tools(self) -> list[MCPTool]:
        """Fetch available tools via GET /tools."""
        result = self._get("/tools")
        return [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("params", {}),
            )
            for t in result.get("tools", [])
        ]

    def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        """Execute a tool via POST /execute?tool_name=<name>."""
        result = self._post("/execute", body=arguments, params={"tool_name": name})
        if result.get("status") == "error":
            return MCPToolResult(
                content=[{"type": "text", "text": result.get("message", str(result))}],
                is_error=True,
            )
        return MCPToolResult(
            content=[{"type": "text", "text": str(result)}],
            is_error=False,
        )

    def list_resources(self) -> list[MCPResource]:
        """Resources are not exposed via the REST servers; returns empty list."""
        return []

    def read_resource(self, uri: str) -> str:
        """Resources are not exposed via the REST servers; returns empty string."""
        return ""


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
