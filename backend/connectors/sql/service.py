"""SQL connector service — business logic layer.

Loads connector credentials from the database, builds a SQLMCPClient,
and exposes methods consumed by the REST API and the sync job.
"""
import logging
import os
from uuid import UUID

from models.connector import Connector
from connectors.base.models import ConnectorConfig
from connectors.sql.mcp_client import SQLMCPClient

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:3003"


class SQLService:
    """Business layer for the SQL MCP connector."""

    connector_type = "sql"

    def __init__(self, locator) -> None:
        self._loc = locator

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self, connector_id: str) -> tuple[SQLMCPClient, Connector]:
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
            server_url=os.environ.get("SQL_MCP_URL", _DEFAULT_SERVER_URL),
            auth_token=creds.encrypted_token if creds else None,
        )
        return SQLMCPClient(config), connector

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
            logger.warning("SQL connection test failed [%s]: %s", connector_id, exc)
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
        """Return all resources (tables/views) exposed by the MCP server."""
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
        """Fetch the raw content of a resource (e.g. table schema) by URI."""
        client, _ = self._build_client(connector_id)
        return client.read_resource(uri)

    def execute_query(
        self,
        connector_id: str,
        query: str,
        database: str | None = None,
        params: list | None = None,
        row_limit: int = 500,
    ) -> dict:
        """Execute a read-only SQL query and return the result."""
        client, _ = self._build_client(connector_id)
        return client.execute_query(query, database, params, row_limit).to_dict()

    def list_tables(
        self,
        connector_id: str,
        database: str | None = None,
        schema: str = "public",
    ) -> dict:
        """List tables available through this connector."""
        client, _ = self._build_client(connector_id)
        return client.list_tables(database, schema).to_dict()

    def describe_table(
        self,
        connector_id: str,
        table: str,
        database: str | None = None,
        schema: str = "public",
    ) -> dict:
        """Return column definitions for a table."""
        client, _ = self._build_client(connector_id)
        return client.describe_table(table, database, schema).to_dict()

    def get_schema(
        self,
        connector_id: str,
        database: str | None = None,
        schema: str = "public",
    ) -> dict:
        """Return the full schema for a database."""
        client, _ = self._build_client(connector_id)
        return client.get_schema(database, schema).to_dict()
