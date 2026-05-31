"""MCP client for a Google Drive MCP server.

Communicates with the MCP server via JSON-RPC 2.0 over HTTP (MCPTransport).
Adds Google Drive-specific convenience methods on top of the base protocol.
"""
import logging

from connectors.base.connector import MCPTransport
from connectors.base.models import ConnectorConfig, MCPToolResult

logger = logging.getLogger(__name__)


class GoogleDriveMCPClient(MCPTransport):
    """JSON-RPC 2.0 client for a Google Drive MCP server."""

    CONNECTOR_TYPE = "google_drive"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    # ------------------------------------------------------------------
    # Google Drive-specific tool wrappers
    # ------------------------------------------------------------------

    def list_files(
        self,
        folder_id: str | None = None,
        query: str | None = None,
        page_size: int = 50,
    ) -> MCPToolResult:
        """List files in Google Drive, optionally filtered by folder or query."""
        args: dict = {"pageSize": page_size}
        if folder_id:
            args["folderId"] = folder_id
        if query:
            args["query"] = query
        return self.call_tool("list_files", args)

    def get_file(self, file_id: str) -> MCPToolResult:
        """Retrieve metadata for a single file."""
        return self.call_tool("get_file", {"fileId": file_id})

    def search_files(self, query: str, page_size: int = 20) -> MCPToolResult:
        """Full-text search across Google Drive files."""
        return self.call_tool("search_files", {"query": query, "pageSize": page_size})

    def export_file(
        self,
        file_id: str,
        mime_type: str = "text/plain",
    ) -> MCPToolResult:
        """Export a Google Docs/Sheets/Slides file to the given MIME type."""
        return self.call_tool("export_file", {"fileId": file_id, "mimeType": mime_type})

    def create_file(
        self,
        name: str,
        content: str,
        folder_id: str | None = None,
        mime_type: str = "text/plain",
    ) -> MCPToolResult:
        """Create a new file in Google Drive."""
        args: dict = {"name": name, "content": content, "mimeType": mime_type}
        if folder_id:
            args["folderId"] = folder_id
        return self.call_tool("create_file", args)

    def update_file(self, file_id: str, content: str) -> MCPToolResult:
        """Update the content of an existing file."""
        return self.call_tool("update_file", {"fileId": file_id, "content": content})

    def delete_file(self, file_id: str) -> MCPToolResult:
        """Move a file to the Google Drive trash."""
        return self.call_tool("delete_file", {"fileId": file_id})

    def list_folders(self, parent_id: str | None = None) -> MCPToolResult:
        """List all folders, optionally under a specific parent."""
        args: dict = {}
        if parent_id:
            args["parentId"] = parent_id
        return self.call_tool("list_folders", args)
