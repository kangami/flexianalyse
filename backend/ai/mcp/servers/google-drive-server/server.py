#!/usr/bin/env python3
"""
Google Drive MCP Server with HTTP Streaming Transport
Provides tools for browsing, searching, and managing Google Drive files
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import uvicorn
from fastmcp import FastMCP
from tools import GoogleDriveTools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "/secrets/google-service-account.json")
HTTP_PORT = int(os.getenv("HTTP_PORT", "3002"))
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

# Initialize Google Drive tools globally
gd_tools = None

def init_tools():
    """Initialize Google Drive tools"""
    global gd_tools
    try:
        gd_tools = GoogleDriveTools(SERVICE_ACCOUNT_JSON)
        logger.info("✓ Google Drive Server tools initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Google Drive Server tools: {e}")
        sys.exit(1)

# Initialize FastAPI with lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup"""
    init_tools()
    logger.info(f"Starting Google Drive MCP Server on HTTP {HTTP_HOST}:{HTTP_PORT}")
    yield
    logger.info("Shutting down Google Drive MCP Server")

app = FastAPI(
    title="Google Drive MCP Server",
    description="Google Drive MCP Server with HTTP Streaming Transport",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize fastMcp
mcp = FastMCP("google-drive-server")


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
async def list_documents(parent_id: str = None, max_results: int = 50) -> dict:
    """List documents in Google Drive"""
    return gd_tools.list_documents(parent_id, max_results)

@mcp.tool()
async def list_folders(parent_id: str = None, max_results: int = 50) -> dict:
    """List folders in Google Drive"""
    return gd_tools.list_folders(parent_id, max_results)

@mcp.tool()
async def get_file_info(file_id: str) -> dict:
    """Get file metadata"""
    return gd_tools.get_file_info(file_id)

@mcp.tool()
async def search_files(query: str, max_results: int = 20) -> dict:
    """Search for files"""
    return gd_tools.search_files(query, max_results)

@mcp.tool()
async def get_folder_tree(folder_id: str = None, max_depth: int = 3) -> dict:
    """Get folder hierarchy"""
    return gd_tools.get_folder_tree(folder_id, max_depth)

# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Google Drive MCP Server",
        "service_account": SERVICE_ACCOUNT_JSON.split("/")[-1]
    }

@app.get("/info")
async def server_info():
    """Server information endpoint"""
    return {
        "service": "Google Drive MCP Server",
        "transport": "HTTP Streaming",
        "platform": "Google Drive",
        "tools": [
            "list_documents",
            "list_folders",
            "get_file_info",
            "search_files",
            "get_folder_tree"
        ],
        "version": "1.0.0"
    }

@app.post("/execute")
async def execute_tool(tool_name: str, params: dict = None):
    """Execute a tool via HTTP"""
    try:
        if params is None:
            params = {}
        
        if tool_name == "list_documents":
            return gd_tools.list_documents(
                params.get("parent_id"),
                params.get("max_results", 50)
            )
        elif tool_name == "list_folders":
            return gd_tools.list_folders(
                params.get("parent_id"),
                params.get("max_results", 50)
            )
        elif tool_name == "get_file_info":
            return gd_tools.get_file_info(params.get("file_id", ""))
        elif tool_name == "search_files":
            return gd_tools.search_files(
                params.get("query", ""),
                params.get("max_results", 20)
            )
        elif tool_name == "get_folder_tree":
            return gd_tools.get_folder_tree(
                params.get("folder_id"),
                params.get("max_depth", 3)
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
                "name": "list_documents",
                "description": "List all documents in Google Drive or a specific folder",
                "params": {
                    "parent_id": "string (optional, None for root)",
                    "max_results": "integer (default: 50)"
                }
            },
            {
                "name": "list_folders",
                "description": "List all folders in Google Drive or a specific parent folder",
                "params": {
                    "parent_id": "string (optional, None for root)",
                    "max_results": "integer (default: 50)"
                }
            },
            {
                "name": "get_file_info",
                "description": "Get detailed information about a specific file",
                "params": {"file_id": "string"}
            },
            {
                "name": "search_files",
                "description": "Search for files by name in Google Drive",
                "params": {
                    "query": "string",
                    "max_results": "integer (default: 20)"
                }
            },
            {
                "name": "get_folder_tree",
                "description": "Get a hierarchical tree of folders and documents",
                "params": {
                    "folder_id": "string (optional, None for root)",
                    "max_depth": "integer (default: 3)"
                }
            }
        ]
    }

if __name__ == "__main__":
    logger.info("Initializing Google Drive MCP Server...")
    uvicorn.run(
        app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info"
    )
