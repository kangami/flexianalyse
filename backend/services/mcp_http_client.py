"""
Simple HTTP client for shared MCP servers.
For MVP: one shared server per connector type.
"""
import httpx
import logging

logger = logging.getLogger(__name__)

# URLs des MCP servers Docker
MCP_SERVERS = {
    "sql":          "http://localhost:3001",
    "google_drive": "http://localhost:3002",
    "sharepoint":   "http://localhost:3003",
}


class MCPHttpClient:
    """Client HTTP simple pour appeler les MCP servers partagés."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/health")
                return r.status_code == 200
        except Exception:
            return False

    async def list_tools(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{self.base_url}/tools")
            r.raise_for_status()
            return r.json()

    async def call_tool(
        self,
        tool_name: str,
        params: dict = None,
        database_url: str = None
    ) -> dict:
        body = {"tool_name": tool_name, "params": params or {}}
        if database_url:
            body["database_url"] = database_url
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base_url}/execute", json=body)
            r.raise_for_status()
            return r.json()

    # --- SQL shortcuts ---
    async def show_tables(self, database_url: str = None) -> dict:
        return await self.call_tool("show_tables", database_url=database_url)

    async def query_database(
        self,
        sql_query: str,
        limit: int = 1000,
        database_url: str = None
    ) -> dict:
        return await self.call_tool("query_database", {
            "sql_query": sql_query,
            "limit": limit
        }, database_url=database_url)

    async def describe_table(
        self,
        table_name: str,
        database_url: str = None
    ) -> dict:
        return await self.call_tool("show_table_schema", {
            "table_name": table_name
        }, database_url=database_url)

    async def get_row_count(
        self,
        table_name: str,
        database_url: str = None
    ) -> dict:
        return await self.call_tool("get_table_row_count", {
            "table_name": table_name
        }, database_url=database_url)

    # --- Google Drive shortcuts ---
    async def list_documents(
        self,
        folder_id: str = None,
        max_results: int = 50
    ) -> dict:
        return await self.call_tool("list_files", {
            "folder_id": folder_id,
            "max_results": max_results
        })

    async def search_files(self, query: str) -> dict:
        return await self.call_tool("search_files", {"query": query})


def get_mcp_client(connector_type: str) -> MCPHttpClient:
    """Retourne un client pour le type de connecteur donné."""
    url = MCP_SERVERS.get(connector_type)
    if not url:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return MCPHttpClient(url)