"""MCP client for a SharePoint MCP server.

Communicates with the MCP server via JSON-RPC 2.0 over HTTP (MCPTransport).
Adds SharePoint-specific convenience methods on top of the base protocol.
"""
import logging

from connectors.base.connector import MCPTransport
from connectors.base.models import ConnectorConfig, MCPToolResult

logger = logging.getLogger(__name__)


class SharePointMCPClient(MCPTransport):
    """JSON-RPC 2.0 client for a SharePoint MCP server."""

    CONNECTOR_TYPE = "sharepoint"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    # ------------------------------------------------------------------
    # SharePoint-specific tool wrappers
    # ------------------------------------------------------------------

    def list_sites(self) -> MCPToolResult:
        """List all SharePoint sites the credentials have access to."""
        return self.call_tool("list_sites", {})

    def list_libraries(self, site_id: str) -> MCPToolResult:
        """List document libraries within a SharePoint site."""
        return self.call_tool("list_libraries", {"siteId": site_id})

    def list_documents(
        self,
        site_id: str,
        library_id: str,
        folder_path: str | None = None,
        page_size: int = 50,
    ) -> MCPToolResult:
        """List documents in a document library, optionally scoped to a folder."""
        args: dict = {"siteId": site_id, "libraryId": library_id, "pageSize": page_size}
        if folder_path:
            args["folderPath"] = folder_path
        return self.call_tool("list_documents", args)

    def read_document(self, site_id: str, document_id: str) -> MCPToolResult:
        """Fetch the text content of a document."""
        return self.call_tool("read_document", {"siteId": site_id, "documentId": document_id})

    def get_document_metadata(self, site_id: str, document_id: str) -> MCPToolResult:
        """Retrieve metadata (author, dates, size…) for a document."""
        return self.call_tool(
            "get_document_metadata",
            {"siteId": site_id, "documentId": document_id},
        )

    def search_documents(
        self,
        query: str,
        site_id: str | None = None,
        page_size: int = 20,
    ) -> MCPToolResult:
        """Full-text search across one or all SharePoint sites."""
        args: dict = {"query": query, "pageSize": page_size}
        if site_id:
            args["siteId"] = site_id
        return self.call_tool("search_documents", args)

    def upload_document(
        self,
        site_id: str,
        library_id: str,
        file_name: str,
        content: str,
        folder_path: str | None = None,
    ) -> MCPToolResult:
        """Upload a new document to a SharePoint library."""
        args: dict = {
            "siteId": site_id,
            "libraryId": library_id,
            "fileName": file_name,
            "content": content,
        }
        if folder_path:
            args["folderPath"] = folder_path
        return self.call_tool("upload_document", args)

    def delete_document(self, site_id: str, document_id: str) -> MCPToolResult:
        """Delete a document from SharePoint."""
        return self.call_tool("delete_document", {"siteId": site_id, "documentId": document_id})

    def list_pages(self, site_id: str) -> MCPToolResult:
        """List SharePoint pages for a given site."""
        return self.call_tool("list_pages", {"siteId": site_id})
