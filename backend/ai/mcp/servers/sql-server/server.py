#!/usr/bin/env python3
"""
Universal SQL Database MCP Server with HTTP Streaming Transport
Supports PostgreSQL, MySQL/MariaDB, Oracle and SQL Server via fastMcp over HTTP.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import uvicorn
from fastmcp import FastMCP
import json
from tools import SQLTools

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional default DB. In production there is none — every /execute call carries
# its own `database_url` — so this stays unset and that's fine.
DATABASE_URL = os.getenv("DATABASE_URL")
# Render injects PORT; docker-compose uses HTTP_PORT. Honour either.
HTTP_PORT = int(os.getenv("PORT") or os.getenv("HTTP_PORT", "3001"))
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

# Initialize SQL tools globally
sql_tools = None

def init_tools():
    """Optionally build the default-DB client.

    Non-fatal: with no (or an unreachable) DATABASE_URL the server still starts
    and serves per-request connections. Exiting here would crash-loop the service
    in production, where connections are always passed per request.
    """
    global sql_tools
    if not DATABASE_URL:
        logger.info("No default DATABASE_URL — server ready for per-request connections")
        return
    try:
        sql_tools = SQLTools(DATABASE_URL)
        logger.info("✓ Default SQL connection initialized")
    except Exception as e:
        logger.warning("Default DB unavailable (%s) — continuing per-request only", e)

# Initialize FastMCP with HTTP transport
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup"""
    init_tools()
    logger.info(f"Starting SQL MCP Server on HTTP {HTTP_HOST}:{HTTP_PORT}")
    yield
    logger.info("Shutting down SQL MCP Server")

app = FastAPI(
    title="SQL MCP Server",
    description="Universal SQL Database MCP Server with HTTP Streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize fastMcp with HTTP transport
mcp = FastMCP("sql-server")

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
async def show_tables() -> dict:
    """List all tables in the database"""
    return sql_tools.show_tables()

@mcp.tool()
async def show_full_schema() -> dict:
    """All tables' columns, primary keys and foreign keys in one call"""
    return sql_tools.show_full_schema()

@mcp.tool()
async def show_table_schema(table_name: str) -> dict:
    """Get table schema"""
    return sql_tools.show_table_schema(table_name)

@mcp.tool()
async def query_database(sql_query: str, limit: int = 1000) -> dict:
    """Execute SELECT query"""
    return sql_tools.query_database(sql_query, limit)

@mcp.tool()
async def get_table_row_count(table_name: str) -> dict:
    """Get row count for table"""
    return sql_tools.get_table_row_count(table_name)

@mcp.tool()
async def get_table_indexes(table_name: str) -> dict:
    """Get indexes for table"""
    return sql_tools.get_table_indexes(table_name)

# ============================================================================
# HTTP ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SQL MCP Server",
        "default_database": DATABASE_URL.split("@")[0] + "@***" if DATABASE_URL else None,
    }

@app.get("/info")
async def server_info():
    """Server information endpoint"""
    return {
        "service": "SQL MCP Server",
        "transport": "HTTP Streaming",
        "database": DATABASE_URL.split("://")[0] if DATABASE_URL else None,
        "tools": [
            "show_tables",
            "show_table_schema",
            "query_database",
            "get_table_row_count",
            "get_table_indexes"
        ],
        "version": "1.0.0"
    }

@app.post("/execute")
async def execute_tool(request: Request):
    body = await request.json()
    tool_name = body.get("tool_name")
    params = body.get("params", {})
    database_url = body.get("database_url")  # ← URL dynamique par requête

    try:
        # Build the client INSIDE the try so a connection failure surfaces as a
        # readable error instead of an opaque "Internal Server Error".
        if database_url:
            from tools import SQLTools
            tools = SQLTools(database_url)
        else:
            tools = sql_tools  # défaut global

        if tool_name == "show_tables":
            return tools.show_tables()
        elif tool_name == "show_full_schema":
            return tools.show_full_schema()
        elif tool_name == "query_database":
            return tools.query_database(
                params.get("sql_query", ""),
                params.get("limit", 1000)
            )
        elif tool_name == "show_table_schema":
            return tools.show_table_schema(params.get("table_name", ""))
        elif tool_name == "get_table_row_count":
            return tools.get_table_row_count(params.get("table_name", ""))
        elif tool_name == "get_table_indexes":
            return tools.get_table_indexes(params.get("table_name", ""))
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Tool '%s' failed: %s", tool_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": [
            {
                "name": "show_tables",
                "description": "List all tables in the database"
            },
            {
                "name": "show_table_schema",
                "description": "Get the schema (columns, types, constraints) for a specific table",
                "params": {"table_name": "string"}
            },
            {
                "name": "query_database",
                "description": "Execute a SELECT query on the database",
                "params": {
                    "sql_query": "string",
                    "limit": "integer (default: 1000)"
                }
            },
            {
                "name": "get_table_row_count",
                "description": "Get the number of rows in a specific table",
                "params": {"table_name": "string"}
            },
            {
                "name": "get_table_indexes",
                "description": "Get all indexes for a specific table",
                "params": {"table_name": "string"}
            }
        ]
    }

if __name__ == "__main__":
    logger.info(f"Initializing SQL MCP Server...")
    uvicorn.run(
        app,
        host=HTTP_HOST,
        port=HTTP_PORT,
        log_level="info"
    )

