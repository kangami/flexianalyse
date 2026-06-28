"""
Simple HTTP client for shared MCP servers.
For MVP: one shared server per connector type.
"""
import os
import httpx
import logging

logger = logging.getLogger(__name__)

# Larger timeout for file downloads (base64 of potentially big files).
DOWNLOAD_TIMEOUT = float(os.getenv("MCP_DOWNLOAD_TIMEOUT", "180"))

MCP_SERVERS = {
    "sql":          "http://localhost:3001",
    "google_drive": "http://localhost:3002",
    "sharepoint":   "http://localhost:3003",
    "dropbox":      "http://localhost:3004",
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
        database_url: str = None,
        access_token: str = None,
        bearer_token: str = None,
        timeout: float = 30,
    ) -> dict:
        body = {"tool_name": tool_name, "params": params or {}}
        if database_url:
            body["database_url"] = database_url
        if access_token:
            body["access_token"] = access_token

        headers = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{self.base_url}/execute",
                json=body,
                headers=headers
            )
            if r.is_error:
                logger.error(
                    "MCP server %s returned %s for tool=%r: %s",
                    self.base_url, r.status_code, tool_name, r.text[:500]
                )
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
        max_results: int = 50,
        access_token: str = None,
        page_token: str = None,
    ) -> dict:
        params = {"parent_id": folder_id, "max_results": max_results}
        if page_token:
            params["page_token"] = page_token
        return await self.call_tool("list_documents", params, access_token=access_token)

    async def search_files(self, query: str, access_token: str = None) -> dict:
        return await self.call_tool("search_files", {"query": query}, access_token=access_token)

    async def download_drive_file_base64(self, file_id: str, mime_type: str, access_token: str = None) -> dict:
        # Downloads can be large → allow more time than the default 30s.
        return await self.call_tool("download_file_base64", {
            "file_id": file_id,
            "mime_type": mime_type,
        }, access_token=access_token, timeout=DOWNLOAD_TIMEOUT)

    # --- Dropbox shortcuts ---
    async def list_dropbox_files(
        self,
        path: str = "",
        recursive: bool = False,
        limit: int = 50,
        bearer_token: str = None,
    ) -> dict:
        return await self.call_tool("list_folder", {
            "path": path,
            "recursive": recursive,
            "limit": limit,
        }, bearer_token=bearer_token)

    async def continue_dropbox_files(
        self,
        cursor: str,
        bearer_token: str = None,
    ) -> dict:
        return await self.call_tool("list_folder_continue", {
            "cursor": cursor,
        }, bearer_token=bearer_token)

    async def search_dropbox_files(
        self,
        query: str,
        path: str = "",
        limit: int = 20,
        bearer_token: str = None,
    ) -> dict:
        return await self.call_tool("search_files", {
            "query": query,
            "path": path,
            "limit": limit,
        }, bearer_token=bearer_token)

    async def download_dropbox_file_text(self, path: str, bearer_token: str = None) -> dict:
        return await self.call_tool(
            "download_file_text", {"path": path},
            bearer_token=bearer_token, timeout=DOWNLOAD_TIMEOUT,
        )

    async def download_dropbox_file_base64(self, path: str, bearer_token: str = None) -> dict:
        return await self.call_tool(
            "download_file_base64", {"path": path},
            bearer_token=bearer_token, timeout=DOWNLOAD_TIMEOUT,
        )


def get_mcp_client(connector_type: str) -> MCPHttpClient:
    url = MCP_SERVERS.get(connector_type)
    if not url:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return MCPHttpClient(url)