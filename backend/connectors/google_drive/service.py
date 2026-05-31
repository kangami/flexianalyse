"""Google Drive connector service — business logic layer.

Loads connector credentials from the database, builds a GoogleDriveMCPClient,
and exposes methods consumed by the REST API and the sync job.
"""
import logging
import os
from uuid import UUID

from models.connector import Connector
from connectors.base.models import ConnectorConfig
from connectors.google_drive.mcp_client import GoogleDriveMCPClient

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:3001"


class GoogleDriveService:
    """Business layer for the Google Drive MCP connector."""

    connector_type = "google_drive"

    def __init__(self, locator) -> None:
        self._loc = locator

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self, connector_id: str) -> tuple[GoogleDriveMCPClient, Connector]:
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
            server_url=os.environ.get("GOOGLE_DRIVE_MCP_URL", _DEFAULT_SERVER_URL),
            auth_token=creds.encrypted_token if creds else None,
        )
        return GoogleDriveMCPClient(config), connector

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
            logger.warning("Google Drive connection test failed [%s]: %s", connector_id, exc)
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
        result = client.call_tool(tool_name, arguments)
        return result.to_dict()

    def list_resources(self, connector_id: str) -> list[dict]:
        """Return all resources (files/folders) exposed by the MCP server."""
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

    def search_files(self, connector_id: str, query: str) -> dict:
        """Full-text search across Google Drive files."""
        client, _ = self._build_client(connector_id)
        return client.search_files(query).to_dict()

    def export_file(self, connector_id: str, file_id: str, mime_type: str = "text/plain") -> dict:
        """Export a Google Workspace file to a plain format."""
        client, _ = self._build_client(connector_id)
        return client.export_file(file_id, mime_type).to_dict()
