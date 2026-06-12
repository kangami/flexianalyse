#!/usr/bin/env python3
"""
SharePoint Online MCP Server with HTTP Streaming Transport
Provides tools for file management and search in SharePoint
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import uvicorn
from fastmcp import FastMCP
from tools import SharePointTools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment
SITE_URL = os.getenv("SHAREPOINT_SITE_URL", "https://tenant.sharepoint.com/sites/sitename")
CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
HTTP_PORT = int(os.getenv("HTTP_PORT", "3003"))
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

# Initialize SharePoint tools globally
sp_tools = None

def init_tools():
    """Initialize SharePoint tools"""
    global sp_tools
    try:
        sp_tools = SharePointTools(SITE_URL, CLIENT_ID, CLIENT_SECRET)
        logger.info("✓ SharePoint Server tools initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize SharePoint Server tools: {e}")
        sys.exit(1)

# Initialize FastAPI with lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup"""
    init_tools()
    logger.info(f"Starting SharePoint MCP Server on HTTP {HTTP_HOST}:{HTTP_PORT}")
    yield
    logger.info("Shutting down SharePoint MCP Server")

app = FastAPI(
    title="SharePoint MCP Server",
    description="SharePoint Online MCP Server with HTTP Streaming Transport",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize fastMcp
mcp = FastMCP("sharepoint-server")

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
async def search_files(query: str, max_results: int = 50) -> dict:
    """Search for files across SharePoint"""
    return sp_tools.search_files(query, max_results)

@mcp.tool()
async def get_file(file_path: str) -> dict:
    """Get file content"""
    return sp_tools.get_file(file_path)

@mcp.tool()
async def upload_file(library_name: str, file_path: str, file_content: bytes) -> dict:
    """Upload file"""
    return sp_tools.upload_file(library_name, file_path, file_content)

@mcp.tool()
async def delete_file(file_path: str) -> dict:
    """Delete file"""
    return sp_tools.delete_file(file_path)

@mcp.tool()
async def move_file(source_path: str, destination_path: str) -> dict:
    """Move file"""
    return sp_tools.move_file(source_path, destination_path)

@mcp.tool()
async def copy_file(source_path: str, destination_path: str) -> dict:
    """Copy file"""
    return sp_tools.copy_file(source_path, destination_path)

@mcp.tool()
async def get_file_versions(file_path: str) -> dict:
    """Get version history"""
    return sp_tools.get_file_versions(file_path)

@mcp.tool()
async def restore_file_version(file_path: str, version_id: int) -> dict:
    """Restore file version"""
    return sp_tools.restore_file_version(file_path, version_id)

# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SharePoint MCP Server",
        "site_url": SITE_URL
    }

@app.get("/info")
async def server_info():
    """Server information endpoint"""
    return {
        "service": "SharePoint MCP Server",
        "transport": "HTTP Streaming",
        "platform": "SharePoint Online",
        "site_url": SITE_URL,
        "tools": [
            "search_files",
            "get_file",
            "upload_file",
            "delete_file",
            "move_file",
            "copy_file",
            "get_file_versions",
            "restore_file_version"
        ],
        "version": "1.0.0"
    }

@app.post("/execute")
async def execute_tool(tool_name: str, params: dict = None):
    """Execute a tool via HTTP"""
    try:
        if params is None:
            params = {}
        
        if tool_name == "search_files":
            return sp_tools.search_files(
                params.get("query", ""),
                params.get("max_results", 50)
            )
        elif tool_name == "get_file":
            return sp_tools.get_file(params.get("file_path", ""))
        elif tool_name == "upload_file":
            return sp_tools.upload_file(
                params.get("library_name", ""),
                params.get("file_path", ""),
                params.get("file_content", b"")
            )
        elif tool_name == "delete_file":
            return sp_tools.delete_file(params.get("file_path", ""))
        elif tool_name == "move_file":
            return sp_tools.move_file(
                params.get("source_path", ""),
                params.get("destination_path", "")
            )
        elif tool_name == "copy_file":
            return sp_tools.copy_file(
                params.get("source_path", ""),
                params.get("destination_path", "")
            )
        elif tool_name == "get_file_versions":
            return sp_tools.get_file_versions(params.get("file_path", ""))
        elif tool_name == "restore_file_version":
            return sp_tools.restore_file_version(
                params.get("file_path", ""),
                params.get("version_id", 0)
            )
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "search_files",
                "description": "Search for files across SharePoint sites",
                "params": {
                    "query": "string",
                    "max_results": "integer (default: 50)"
                }
            },
            {
                "name": "get_file",
                "description": "Download/read a specific file by path",
                "params": {"file_path": "string"}
            },
            {
                "name": "upload_file",
                "description": "Upload a file to a SharePoint document library",
                "params": {
                    "library_name": "string",
                    "file_path": "string",
                    "file_content": "bytes"
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file from SharePoint",
                "params": {"file_path": "string"}
            },
            {
                "name": "move_file",
                "description": "Move a file to another folder or library",
                "params": {
                    "source_path": "string",
                    "destination_path": "string"
                }
            },
            {
                "name": "copy_file",
                "description": "Copy a file to another location",
                "params": {
                    "source_path": "string",
                    "destination_path": "string"
                }
            },
            {
                "name": "get_file_versions",
                "description": "Get version history of a file",
                "params": {"file_path": "string"}
            },
            {
                "name": "restore_file_version",
                "description": "Restore a previous version of a file",
                "params": {
                    "file_path": "string",
                    "version_id": "integer"
                }
            }
        ]
    }

if __name__ == "__main__":
    logger.info("Initializing SharePoint MCP Server...")
    uvicorn.run(
        app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info"
    )


@app.tool()
def get_file(file_path: str) -> dict:
    """
    Download/read a specific file by path
    
    Args:
        file_path: SharePoint file path (e.g., /sites/sitename/Shared Documents/filename.pdf)
    
    Returns:
        Dictionary with file metadata and access information
    """
    return sp_tools.get_file(file_path)


@app.tool()
def upload_file(library_name: str, file_path: str, file_content: bytes) -> dict:
    """
    Upload a file to a SharePoint document library
    
    Args:
        library_name: Target document library name
        file_path: Target path in library (e.g., 'folder/file.txt')
        file_content: File content as bytes
    
    Returns:
        Dictionary with upload status
    """
    return sp_tools.upload_file(library_name, file_path, file_content)


@app.tool()
def delete_file(file_path: str) -> dict:
    """
    Delete a file from SharePoint
    
    Args:
        file_path: SharePoint file path to delete
    
    Returns:
        Dictionary with deletion status
    """
    return sp_tools.delete_file(file_path)


@app.tool()
def move_file(source_path: str, destination_path: str) -> dict:
    """
    Move a file to another folder or library
    
    Args:
        source_path: Current file path
        destination_path: Target path
    
    Returns:
        Dictionary with move status
    """
    return sp_tools.move_file(source_path, destination_path)


@app.tool()
def copy_file(source_path: str, destination_path: str) -> dict:
    """
    Copy a file to another location
    
    Args:
        source_path: Current file path
        destination_path: Target path
    
    Returns:
        Dictionary with copy status
    """
    return sp_tools.copy_file(source_path, destination_path)


@app.tool()
def get_file_versions(file_path: str) -> dict:
    """
    Get version history of a file
    
    Args:
        file_path: SharePoint file path
    
    Returns:
        Dictionary with version history including timestamps and creators
    """
    return sp_tools.get_file_versions(file_path)


@app.tool()
def restore_file_version(file_path: str, version_id: int) -> dict:
    """
    Restore a previous version of a file
    
    Args:
        file_path: SharePoint file path
        version_id: Version ID to restore to
    
    Returns:
        Dictionary with restoration status
    """
    return sp_tools.restore_file_version(file_path, version_id)


@app.resource()
def sharepoint_info() -> str:
    """
    Provide information about SharePoint server capabilities
    
    Returns:
        String with server information and available operations
    """
    return f"""
    SharePoint Online MCP Server - Information
    ==========================================
    
    Site URL: {SITE_URL}
    
    Authentication: Azure AD App Registration
    - Client ID: {CLIENT_ID[:20]}***
    - Configured via environment variables
    
    Available Tools:
    1. search_files(query, max_results) - Search for files
    2. get_file(file_path) - Download/read file
    3. upload_file(library_name, file_path, file_content) - Upload file
    4. delete_file(file_path) - Delete file
    5. move_file(source_path, destination_path) - Move file
    6. copy_file(source_path, destination_path) - Copy file
    7. get_file_versions(file_path) - List version history
    8. restore_file_version(file_path, version_id) - Restore previous version
    
    Notes:
    - Requires Office365 REST Python Client library
    - Supports document libraries and folders
    - Version management available for all files
    - All operations use OAuth 2.0 authentication
    """


if __name__ == "__main__":
    logger.info("Starting SharePoint MCP Server on stdio transport...")
    app.run()
