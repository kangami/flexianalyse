#!/usr/bin/env python3
"""
Dropbox MCP Server with HTTP Transport

Provides tools for browsing, searching, and downloading Dropbox files.
The user's OAuth access token must be passed with every request via:
    Authorization: Bearer <dropbox_access_token>
"""
import os
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastmcp import FastMCP

from tools import DropboxTools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

HTTP_PORT = int(os.getenv("HTTP_PORT", "3004"))
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

app = FastAPI(
    title="Dropbox MCP Server",
    description=(
        "Dropbox MCP Server — exposes Dropbox file tools. "
        "Pass the user's OAuth token via Authorization: Bearer <token>."
    ),
    version="1.0.0",
)

# Initialize FastMCP
mcp = FastMCP("dropbox-server")


# ============================================================================
# TOOL IMPLEMENTATIONS  (FastMCP protocol transport)
# access_token is required as a parameter since Dropbox uses per-user OAuth
# ============================================================================

@mcp.tool()
async def list_folder(access_token: str, path: str = "", recursive: bool = False, limit: int = 50) -> dict:
    """List files and folders inside a Dropbox path"""
    return DropboxTools(access_token).list_folder(path, recursive, limit)

@mcp.tool()
async def search_files(access_token: str, query: str, path: str = "", limit: int = 20) -> dict:
    """Search for files and folders across Dropbox"""
    return DropboxTools(access_token).search_files(query, path, limit)

@mcp.tool()
async def get_metadata(access_token: str, path: str) -> dict:
    """Get metadata for a specific file or folder path"""
    return DropboxTools(access_token).get_metadata(path)

@mcp.tool()
async def download_file_text(access_token: str, path: str) -> dict:
    """Download a Dropbox file and return its text content"""
    return DropboxTools(access_token).download_file_text(path)

@mcp.tool()
async def download_file_base64(access_token: str, path: str) -> dict:
    """Download a Dropbox file and return its raw bytes as base64 (binary-safe)"""
    return DropboxTools(access_token).download_file_base64(path)


# ---------------------------------------------------------------------------
# Health / info
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check — no auth required."""
    return {"status": "healthy", "service": "Dropbox MCP Server"}


@app.get("/info")
async def server_info():
    """Server metadata."""
    return {
        "service": "Dropbox MCP Server",
        "transport": "HTTP",
        "platform": "Dropbox",
        "auth": "Bearer token (per-request)",
        "tools": ["list_folder", "search_files", "get_metadata", "download_file_text", "download_file_base64"],
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Tools catalogue
# ---------------------------------------------------------------------------

@app.get("/tools")
async def list_tools():
    """List available Dropbox tools."""
    return {
        "tools": [
            {
                "name": "list_folder",
                "description": "List files and folders inside a Dropbox path",
                "params": {
                    "path": "string (default: '' = root)",
                    "recursive": "boolean (default: false)",
                    "limit": "integer (default: 50, max: 2000)",
                },
            },
            {
                "name": "search_files",
                "description": "Search for files and folders across Dropbox",
                "params": {
                    "query": "string",
                    "path": "string (default: '' = entire Dropbox)",
                    "limit": "integer (default: 20, max: 100)",
                },
            },
            {
                "name": "get_metadata",
                "description": "Get metadata for a specific file or folder path",
                "params": {"path": "string (must start with '/')"},
            },
            {
                "name": "download_file_text",
                "description": "Download a file and return its text content",
                "params": {"path": "string (must start with '/')"},
            },
            {
                "name": "download_file_base64",
                "description": "Download a file and return its raw bytes as base64 (binary-safe, use for PDF/DOCX/XLSX)",
                "params": {"path": "string (must start with '/')"},
            },
        ]
    }


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

@app.post("/execute")
async def execute_tool(request: Request):
    """Execute a Dropbox tool.

    Body: {"tool_name": "...", "params": {...}}
    Authorization: Bearer <token> header is required.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization: Bearer <dropbox_access_token> header required",
        )
    access_token = auth[len("Bearer "):]
    tools = DropboxTools(access_token)

    body = await request.json()
    tool_name = body.get("tool_name")
    params = body.get("params", {})

    logger.info("Executing tool '%s' with params: %s", tool_name, params)

    try:
        if tool_name == "list_folder":
            return tools.list_folder(
                path=params.get("path", ""),
                recursive=bool(params.get("recursive", False)),
                limit=int(params.get("limit", 50)),
            )
        elif tool_name == "search_files":
            return tools.search_files(
                query=params.get("query", ""),
                path=params.get("path", ""),
                limit=int(params.get("limit", 20)),
            )
        elif tool_name == "get_metadata":
            return tools.get_metadata(path=params.get("path", ""))
        elif tool_name == "download_file_text":
            return tools.download_file_text(path=params.get("path", ""))
        elif tool_name == "download_file_base64":
            return tools.download_file_base64(path=params.get("path", ""))
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Tool '%s' execution error: %s", tool_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    logger.info("Starting Dropbox MCP Server on %s:%s", HTTP_HOST, HTTP_PORT)
    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT, log_level="info")
