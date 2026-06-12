#!/usr/bin/env python3
"""
MCP Server HTTP Streaming Client Examples

This script demonstrates how to communicate with the three MCP servers
using HTTP streaming transport with async/await patterns.
"""

import asyncio
import json
from typing import Any, Dict, Optional
import httpx


class MCPHTTPClient:
    """Generic MCP Server HTTP Client"""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def get_info(self) -> Dict[str, Any]:
        """Get server information"""
        response = await self.client.get(f"{self.base_url}/info")
        response.raise_for_status()
        return response.json()
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        response = await self.client.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json()
    
    async def execute_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a tool with parameters"""
        if params is None:
            params = {}
        
        response = await self.client.post(
            f"{self.base_url}/execute",
            params={"tool_name": tool_name},
            json={"params": params}
        )
        response.raise_for_status()
        return response.json()
    
    async def stream_results(self, tool_name: str, params: Optional[Dict[str, Any]] = None):
        """Stream tool results (generator)"""
        if params is None:
            params = {}
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/execute",
            params={"tool_name": tool_name},
            json={"params": params}
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    yield json.loads(line)


# ============================================================================
# SQL SERVER EXAMPLES
# ============================================================================

class SQLServerClient(MCPHTTPClient):
    """SQL MCP Server Client"""
    
    async def show_tables(self) -> Dict[str, Any]:
        """List all tables"""
        return await self.execute_tool("show_tables")
    
    async def show_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema"""
        return await self.execute_tool("show_table_schema", {"table_name": table_name})
    
    async def query_database(self, sql_query: str, limit: int = 1000) -> Dict[str, Any]:
        """Execute a SELECT query"""
        return await self.execute_tool(
            "query_database",
            {"sql_query": sql_query, "limit": limit}
        )
    
    async def get_table_row_count(self, table_name: str) -> Dict[str, Any]:
        """Get row count for a table"""
        return await self.execute_tool("get_table_row_count", {"table_name": table_name})
    
    async def get_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """Get table indexes"""
        return await self.execute_tool("get_table_indexes", {"table_name": table_name})


# ============================================================================
# GOOGLE DRIVE SERVER EXAMPLES
# ============================================================================

class GoogleDriveServerClient(MCPHTTPClient):
    """Google Drive MCP Server Client"""
    
    async def list_documents(self, parent_id: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        """List documents"""
        return await self.execute_tool(
            "list_documents",
            {"parent_id": parent_id, "max_results": max_results}
        )
    
    async def list_folders(self, parent_id: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        """List folders"""
        return await self.execute_tool(
            "list_folders",
            {"parent_id": parent_id, "max_results": max_results}
        )
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information"""
        return await self.execute_tool("get_file_info", {"file_id": file_id})
    
    async def search_files(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Search for files"""
        return await self.execute_tool(
            "search_files",
            {"query": query, "max_results": max_results}
        )
    
    async def get_folder_tree(self, folder_id: Optional[str] = None, max_depth: int = 3) -> Dict[str, Any]:
        """Get folder hierarchy"""
        return await self.execute_tool(
            "get_folder_tree",
            {"folder_id": folder_id, "max_depth": max_depth}
        )


# ============================================================================
# SHAREPOINT SERVER EXAMPLES
# ============================================================================

class SharePointServerClient(MCPHTTPClient):
    """SharePoint MCP Server Client"""
    
    async def search_files(self, query: str, max_results: int = 50) -> Dict[str, Any]:
        """Search for files"""
        return await self.execute_tool(
            "search_files",
            {"query": query, "max_results": max_results}
        )
    
    async def get_file(self, file_path: str) -> Dict[str, Any]:
        """Download/read a file"""
        return await self.execute_tool("get_file", {"file_path": file_path})
    
    async def upload_file(self, library_name: str, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """Upload a file"""
        return await self.execute_tool(
            "upload_file",
            {
                "library_name": library_name,
                "file_path": file_path,
                "file_content": file_content.hex()
            }
        )
    
    async def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file"""
        return await self.execute_tool("delete_file", {"file_path": file_path})
    
    async def move_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """Move a file"""
        return await self.execute_tool(
            "move_file",
            {"source_path": source_path, "destination_path": destination_path}
        )
    
    async def copy_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        """Copy a file"""
        return await self.execute_tool(
            "copy_file",
            {"source_path": source_path, "destination_path": destination_path}
        )
    
    async def get_file_versions(self, file_path: str) -> Dict[str, Any]:
        """Get version history"""
        return await self.execute_tool("get_file_versions", {"file_path": file_path})
    
    async def restore_file_version(self, file_path: str, version_id: int) -> Dict[str, Any]:
        """Restore a previous version"""
        return await self.execute_tool(
            "restore_file_version",
            {"file_path": file_path, "version_id": version_id}
        )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_sql_server():
    """Example: SQL Server operations"""
    print("\n" + "=" * 60)
    print("SQL SERVER EXAMPLES")
    print("=" * 60)
    
    async with SQLServerClient("http://localhost:3001") as client:
        try:
            # Check health
            print("\n1. Health Check:")
            health = await client.health_check()
            print(json.dumps(health, indent=2))
            
            # Get info
            print("\n2. Server Info:")
            info = await client.get_info()
            print(json.dumps(info, indent=2))
            
            # List tables
            print("\n3. Available Tables:")
            tables = await client.show_tables()
            print(json.dumps(tables, indent=2))
            
            # Show table schema
            if "table_names" in tables and tables["table_names"]:
                table_name = tables["table_names"][0]
                print(f"\n4. Schema for table '{table_name}':")
                schema = await client.show_table_schema(table_name)
                print(json.dumps(schema, indent=2))
                
                # Get row count
                print(f"\n5. Row count for '{table_name}':")
                count = await client.get_table_row_count(table_name)
                print(json.dumps(count, indent=2))
            
            # Query database
            print("\n6. Query Database:")
            query_result = await client.query_database(
                "SELECT * FROM information_schema.tables LIMIT 5",
                limit=10
            )
            print(json.dumps(query_result, indent=2)[:500] + "...")
            
        except Exception as e:
            print(f"Error: {e}")


async def example_google_drive():
    """Example: Google Drive operations"""
    print("\n" + "=" * 60)
    print("GOOGLE DRIVE SERVER EXAMPLES")
    print("=" * 60)
    
    async with GoogleDriveServerClient("http://localhost:3002") as client:
        try:
            # Check health
            print("\n1. Health Check:")
            health = await client.health_check()
            print(json.dumps(health, indent=2))
            
            # Get info
            print("\n2. Server Info:")
            info = await client.get_info()
            print(json.dumps(info, indent=2))
            
            # List documents
            print("\n3. List Documents:")
            docs = await client.list_documents(max_results=10)
            print(json.dumps(docs, indent=2)[:500] + "...")
            
            # List folders
            print("\n4. List Folders:")
            folders = await client.list_folders(max_results=10)
            print(json.dumps(folders, indent=2)[:500] + "...")
            
            # Search files
            print("\n5. Search Files:")
            search_result = await client.search_files("budget", max_results=5)
            print(json.dumps(search_result, indent=2)[:500] + "...")
            
        except Exception as e:
            print(f"Error: {e}")


async def example_sharepoint():
    """Example: SharePoint operations"""
    print("\n" + "=" * 60)
    print("SHAREPOINT SERVER EXAMPLES")
    print("=" * 60)
    
    async with SharePointServerClient("http://localhost:3003") as client:
        try:
            # Check health
            print("\n1. Health Check:")
            health = await client.health_check()
            print(json.dumps(health, indent=2))
            
            # Get info
            print("\n2. Server Info:")
            info = await client.get_info()
            print(json.dumps(info, indent=2))
            
            # Search files
            print("\n3. Search Files:")
            search_result = await client.search_files("report", max_results=5)
            print(json.dumps(search_result, indent=2)[:500] + "...")
            
            # List tools
            print("\n4. Available Tools:")
            tools = await client.list_tools()
            print(json.dumps(tools, indent=2)[:500] + "...")
            
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("MCP SERVER HTTP STREAMING CLIENT EXAMPLES")
    print("=" * 60)
    print("\nMake sure all servers are running:")
    print("  docker-compose up -d")
    
    try:
        await example_sql_server()
    except Exception as e:
        print(f"SQL Server example failed: {e}")
    
    try:
        await example_google_drive()
    except Exception as e:
        print(f"Google Drive example failed: {e}")
    
    try:
        await example_sharepoint()
    except Exception as e:
        print(f"SharePoint example failed: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
