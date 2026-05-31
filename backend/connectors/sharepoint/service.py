"""SharePoint connector service — business logic layer.

Loads connector credentials from the database, builds a SharePointMCPClient,
and exposes methods consumed by the REST API and the sync job.
"""
import logging
import os
from uuid import UUID

from models.connector import Connector
from connectors.base.models import ConnectorConfig
from connectors.sharepoint.mcp_client import SharePointMCPClient

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:3002"


class SharePointService:
    """Business layer for the SharePoint MCP connector."""

    connector_type = "sharepoint"

    def __init__(self, locator) -> None:
        self._loc = locator

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self, connector_id: str) -> tuple[SharePointMCPClient, Connector]:
        """Resolve credentials from DB and return a ready-to-use MCP client."""
        connector = self._loc.connectors.get_by_id(UUID(connector_id))
        if not connector:
            raise ValueError(f"Connector '{connector_id}' not found")
        if connector.type != self.connector_type:
            raise TypeError(
                f"Expected connector type '{self.connector_type}', got '{connector.type}'"
            )

        creds = self._loc.connector_credentials.get_by_connector(UUID(connector_id))
        config = ConnectorConfig(
            server_url=os.environ.get("SHAREPOINT_MCP_URL", _DEFAULT_SERVER_URL),
            auth_token=creds.encrypted_token if creds else None,
        )
        return SharePointMCPClient(config), connector

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def test_connection(self, connector_id: str) -> bool:
        """Return True if the MCP server responds to an initialize call."""
        try:
            client, _ = self._build_client(connector_id)
            client.initialize()
            return True
        except Exception as exc:
            logger.warning("SharePoint connection test failed [%s]: %s", connector_id, exc)
            return False

    def list_tools(self, connector_id: str) -> list[dict]:
        """Return serialised tool descriptors available on the MCP server."""
        client, _ = self._build_client(connector_id)
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in client.list_tools()
        ]

    def call_tool(self, connector_id: str, tool_name: str, arguments: dict) -> dict:
        """Invoke a tool on the MCP server and return its result as a dict."""
        client, _ = self._build_client(connector_id)
        return client.call_tool(tool_name, arguments).to_dict()

    def list_resources(self, connector_id: str) -> list[dict]:
        """Return all resources (documents/pages) exposed by the MCP server."""
        client, _ = self._build_client(connector_id)
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mime_type": r.mime_type,
            }
            for r in client.list_resources()
        ]

    def read_resource(self, connector_id: str, uri: str) -> str:
        """Fetch the raw text content of a resource identified by *uri*."""
        client, _ = self._build_client(connector_id)
        return client.read_resource(uri)

    def list_sites(self, connector_id: str) -> dict:
        """List SharePoint sites accessible through this connector."""
        client, _ = self._build_client(connector_id)
        return client.list_sites().to_dict()

    def list_libraries(self, connector_id: str, site_id: str) -> dict:
        """List document libraries for a SharePoint site."""
        client, _ = self._build_client(connector_id)
        return client.list_libraries(site_id).to_dict()

    def search_documents(self, connector_id: str, query: str, site_id: str | None = None) -> dict:
        """Full-text document search within SharePoint."""
        client, _ = self._build_client(connector_id)
        return client.search_documents(query, site_id).to_dict()
