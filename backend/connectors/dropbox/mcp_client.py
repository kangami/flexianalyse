"""MCP client for the Dropbox MCP server."""
import ast

from connectors.base.connector import MCPTransport
from connectors.base.models import ConnectorConfig, MCPResource, MCPToolResult


class DropboxMCPClient(MCPTransport):
    """HTTP client for Dropbox MCP tools."""

    CONNECTOR_TYPE = "dropbox"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _execute(self, tool_name: str, arguments: dict) -> dict:
        return self._post("/execute", body=arguments, params={"tool_name": tool_name})

    def _tool_result(self, payload: dict) -> MCPToolResult:
        return MCPToolResult(
            content=[{"type": "text", "text": str(payload)}],
            is_error=payload.get("status") == "error",
        )

    def call_tool(self, name: str, arguments: dict) -> MCPToolResult:
        return self._tool_result(self._execute(name, arguments))

    def list_files(
        self,
        path: str = "",
        recursive: bool = False,
        limit: int = 50,
    ) -> MCPToolResult:
        return self.call_tool(
            "list_folder",
            {"path": path, "recursive": recursive, "limit": limit},
        )

    def search_files(self, query: str, path: str = "", limit: int = 20) -> MCPToolResult:
        return self.call_tool(
            "search_files",
            {"query": query, "path": path, "limit": limit},
        )

    def get_file_metadata(self, path: str) -> MCPToolResult:
        return self.call_tool("get_metadata", {"path": path})

    def download_file_text(self, path: str) -> MCPToolResult:
        return self.call_tool("download_file_text", {"path": path})

    def list_resources(self) -> list[MCPResource]:
        payload = self._execute("list_folder", {"path": "", "recursive": True, "limit": 200})
        entries = payload.get("entries", [])
        resources: list[MCPResource] = []
        for item in entries:
            if item.get("tag") == "folder":
                continue
            resources.append(
                MCPResource(
                    uri=item.get("path_lower") or item.get("path_display") or item.get("id"),
                    name=item.get("name", "Dropbox file"),
                    description=item.get("path_display", ""),
                    mime_type=item.get("mime_type"),
                    metadata=item,
                )
            )
        return resources

    def read_resource(self, uri: str) -> str:
        result = self.download_file_text(uri)
        try:
            payload = ast.literal_eval(result.text())
        except (SyntaxError, ValueError):
            return result.text()
        return payload.get("text", result.text())
