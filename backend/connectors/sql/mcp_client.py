"""MCP client for a SQL MCP server.

Communicates with the MCP server via JSON-RPC 2.0 over HTTP (MCPTransport).
Adds SQL-specific convenience methods on top of the base protocol.
"""
import logging

from connectors.base.connector import MCPTransport
from connectors.base.models import ConnectorConfig, MCPToolResult

logger = logging.getLogger(__name__)


class SQLMCPClient(MCPTransport):
    """JSON-RPC 2.0 client for a SQL MCP server."""

    CONNECTOR_TYPE = "sql"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    # ------------------------------------------------------------------
    # SQL-specific tool wrappers
    # ------------------------------------------------------------------

    def list_databases(self) -> MCPToolResult:
        """List all databases accessible through this connector."""
        return self.call_tool("list_databases", {})

    def list_tables(self, database: str | None = None, schema: str = "public") -> MCPToolResult:
        """List tables in a database/schema."""
        args: dict = {"schema": schema}
        if database:
            args["database"] = database
        return self.call_tool("list_tables", args)

    def describe_table(
        self,
        table: str,
        database: str | None = None,
        schema: str = "public",
    ) -> MCPToolResult:
        """Return the full DDL / column definitions for a table."""
        args: dict = {"table": table, "schema": schema}
        if database:
            args["database"] = database
        return self.call_tool("describe_table", args)

    def execute_query(
        self,
        query: str,
        database: str | None = None,
        params: list | None = None,
        row_limit: int = 500,
    ) -> MCPToolResult:
        """Execute a read-only SQL query and return the result set.

        The MCP server is expected to enforce read-only access (SELECT only).
        """
        args: dict = {"query": query, "rowLimit": row_limit}
        if database:
            args["database"] = database
        if params:
            args["params"] = params
        return self.call_tool("execute_query", args)

    def get_schema(
        self,
        database: str | None = None,
        schema: str = "public",
    ) -> MCPToolResult:
        """Return the full schema (all tables + columns) for a database."""
        args: dict = {"schema": schema}
        if database:
            args["database"] = database
        return self.call_tool("get_schema", args)

    def list_views(
        self,
        database: str | None = None,
        schema: str = "public",
    ) -> MCPToolResult:
        """List all views in a database/schema."""
        args: dict = {"schema": schema}
        if database:
            args["database"] = database
        return self.call_tool("list_views", args)

    def get_table_stats(
        self,
        table: str,
        database: str | None = None,
        schema: str = "public",
    ) -> MCPToolResult:
        """Return row count and size statistics for a table."""
        args: dict = {"table": table, "schema": schema}
        if database:
            args["database"] = database
        return self.call_tool("get_table_stats", args)
