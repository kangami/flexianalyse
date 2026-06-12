# MCP Server HTTP Streaming Transport

This document describes the HTTP streaming transport layer for the 3 MCP servers: SQL, Google Drive, and SharePoint.

## Overview

All three MCP servers now use **HTTP streaming transport** with FastAPI and uvicorn instead of stdio transport. This enables:

- **Scalability**: Multiple clients can connect simultaneously
- **Streaming**: Large result sets can be streamed efficiently
- **REST API**: Standard HTTP methods for tool execution
- **Health Monitoring**: Built-in health check endpoints
- **Containerization**: Docker-based deployment with proper HTTP port mapping

## Server Details

### SQL Server
- **Port**: 3001
- **Container Name**: mcp-sql-server
- **Base URL**: `http://localhost:3001`
- **Supports**: PostgreSQL, MySQL, Oracle

### Google Drive Server
- **Port**: 3002
- **Container Name**: mcp-google-drive-server
- **Base URL**: `http://localhost:3002`
- **Requires**: Google Service Account JSON

### SharePoint Server
- **Port**: 3003
- **Container Name**: mcp-sharepoint-server
- **Base URL**: `http://localhost:3003`
- **Requires**: Azure OAuth credentials

## HTTP Endpoints

Each server provides the following standard endpoints:

### 1. Health Check
```
GET /health
```
Returns server health status.

**Example Response**:
```json
{
  "status": "healthy",
  "service": "SQL MCP Server",
  "database_url": "postgresql://***"
}
```

### 2. Server Information
```
GET /info
```
Returns server capabilities and version.

**Example Response**:
```json
{
  "service": "SQL MCP Server",
  "transport": "HTTP Streaming",
  "database": "postgresql",
  "tools": [
    "show_tables",
    "show_table_schema",
    "query_database",
    "get_table_row_count",
    "get_table_indexes"
  ],
  "version": "1.0.0"
}
```

### 3. List Tools
```
GET /tools
```
Returns detailed information about all available tools.

**Example Response**:
```json
{
  "tools": [
    {
      "name": "show_tables",
      "description": "List all tables in the database"
    },
    {
      "name": "query_database",
      "description": "Execute a SELECT query on the database",
      "params": {
        "sql_query": "string",
        "limit": "integer (default: 1000)"
      }
    }
  ]
}
```

### 4. Execute Tool
```
POST /execute?tool_name=<name>
Content-Type: application/json

{
  "params": {
    "key": "value"
  }
}
```

Executes a specific tool with parameters.

## Python Client Examples

### Using httpx (Async)

```python
import httpx

async def query_sql_database():
    async with httpx.AsyncClient() as client:
        # Check health
        health = await client.get("http://localhost:3001/health")
        print(health.json())
        
        # Get available tools
        tools = await client.get("http://localhost:3001/tools")
        print(tools.json())
        
        # Execute a tool
        response = await client.post(
            "http://localhost:3001/execute?tool_name=query_database",
            json={
                "params": {
                    "sql_query": "SELECT * FROM users LIMIT 10",
                    "limit": 100
                }
            }
        )
        results = response.json()
        print(results)
```

### Using requests (Sync)

```python
import requests

def query_sql_database():
    base_url = "http://localhost:3001"
    
    # Health check
    response = requests.get(f"{base_url}/health")
    print(response.json())
    
    # Execute tool
    response = requests.post(
        f"{base_url}/execute",
        params={"tool_name": "query_database"},
        json={
            "params": {
                "sql_query": "SELECT * FROM users LIMIT 10",
                "limit": 100
            }
        }
    )
    print(response.json())
```

## JavaScript/Node.js Client Example

```javascript
const axios = require('axios');

async function queryDatabase() {
    const baseURL = 'http://localhost:3001';
    
    try {
        // Health check
        const health = await axios.get(`${baseURL}/health`);
        console.log('Health:', health.data);
        
        // List tools
        const tools = await axios.get(`${baseURL}/tools`);
        console.log('Tools:', tools.data);
        
        // Execute tool
        const response = await axios.post(
            `${baseURL}/execute?tool_name=query_database`,
            {
                params: {
                    sql_query: 'SELECT * FROM users LIMIT 10',
                    limit: 100
                }
            }
        );
        console.log('Query Results:', response.data);
    } catch (error) {
        console.error('Error:', error.message);
    }
}

queryDatabase();
```

## SQL Server Tools

### 1. show_tables
Lists all tables in the database.

```bash
curl http://localhost:3001/execute?tool_name=show_tables
```

### 2. show_table_schema
Get table structure (columns, types, constraints).

```bash
curl http://localhost:3001/execute?tool_name=show_table_schema \
  -H "Content-Type: application/json" \
  -d '{"params": {"table_name": "users"}}'
```

### 3. query_database
Execute a SELECT query.

```bash
curl http://localhost:3001/execute?tool_name=query_database \
  -H "Content-Type: application/json" \
  -d '{"params": {"sql_query": "SELECT * FROM users LIMIT 10", "limit": 100}}'
```

### 4. get_table_row_count
Get row count for a table.

```bash
curl http://localhost:3001/execute?tool_name=get_table_row_count \
  -H "Content-Type: application/json" \
  -d '{"params": {"table_name": "users"}}'
```

### 5. get_table_indexes
Get all indexes for a table.

```bash
curl http://localhost:3001/execute?tool_name=get_table_indexes \
  -H "Content-Type: application/json" \
  -d '{"params": {"table_name": "users"}}'
```

## Google Drive Server Tools

### 1. list_documents
List documents in a folder.

```bash
curl http://localhost:3002/execute?tool_name=list_documents \
  -H "Content-Type: application/json" \
  -d '{"params": {"parent_id": null, "max_results": 50}}'
```

### 2. list_folders
List folders.

```bash
curl http://localhost:3002/execute?tool_name=list_folders \
  -H "Content-Type: application/json" \
  -d '{"params": {"parent_id": null, "max_results": 50}}'
```

### 3. get_file_info
Get file metadata.

```bash
curl http://localhost:3002/execute?tool_name=get_file_info \
  -H "Content-Type: application/json" \
  -d '{"params": {"file_id": "file123"}}'
```

### 4. search_files
Search for files.

```bash
curl http://localhost:3002/execute?tool_name=search_files \
  -H "Content-Type: application/json" \
  -d '{"params": {"query": "budget", "max_results": 20}}'
```

### 5. get_folder_tree
Get hierarchical folder structure.

```bash
curl http://localhost:3002/execute?tool_name=get_folder_tree \
  -H "Content-Type: application/json" \
  -d '{"params": {"folder_id": null, "max_depth": 3}}'
```

## SharePoint Server Tools

### 1. search_files
Search files in SharePoint.

```bash
curl http://localhost:3003/execute?tool_name=search_files \
  -H "Content-Type: application/json" \
  -d '{"params": {"query": "budget", "max_results": 50}}'
```

### 2. get_file
Download/read a file.

```bash
curl http://localhost:3003/execute?tool_name=get_file \
  -H "Content-Type: application/json" \
  -d '{"params": {"file_path": "/sites/project/Documents/file.docx"}}'
```

### 3. upload_file
Upload a file to SharePoint.

```bash
curl http://localhost:3003/execute?tool_name=upload_file \
  -H "Content-Type: application/json" \
  -d '{"params": {"library_name": "Documents", "file_path": "report.pdf", "file_content": "base64_encoded_content"}}'
```

### 4. delete_file
Delete a file.

```bash
curl http://localhost:3003/execute?tool_name=delete_file \
  -H "Content-Type: application/json" \
  -d '{"params": {"file_path": "/sites/project/Documents/old_file.docx"}}'
```

### 5. move_file
Move a file to another location.

```bash
curl http://localhost:3003/execute?tool_name=move_file \
  -H "Content-Type: application/json" \
  -d '{"params": {"source_path": "/sites/project/Documents/file.docx", "destination_path": "/sites/project/Archive/file.docx"}}'
```

### 6. copy_file
Copy a file.

```bash
curl http://localhost:3003/execute?tool_name=copy_file \
  -H "Content-Type: application/json" \
  -d '{"params": {"source_path": "/sites/project/Documents/file.docx", "destination_path": "/sites/project/Drafts/file_copy.docx"}}'
```

### 7. get_file_versions
Get version history.

```bash
curl http://localhost:3003/execute?tool_name=get_file_versions \
  -H "Content-Type: application/json" \
  -d '{"params": {"file_path": "/sites/project/Documents/file.docx"}}'
```

### 8. restore_file_version
Restore a previous version.

```bash
curl http://localhost:3003/execute?tool_name=restore_file_version \
  -H "Content-Type: application/json" \
  -d '{"params": {"file_path": "/sites/project/Documents/file.docx", "version_id": 3}}'
```

## Streaming Large Result Sets

For streaming large responses, clients can use streaming requests:

### Python (httpx)

```python
async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:3001/execute?tool_name=query_database",
        json={
            "params": {
                "sql_query": "SELECT * FROM large_table",
                "limit": 10000
            }
        }
    ) as response:
        async for line in response.aiter_lines():
            print(line)
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:3001/execute?tool_name=query_database', {
    method: 'POST',
    body: JSON.stringify({
        params: {
            sql_query: 'SELECT * FROM large_table',
            limit: 10000
        }
    })
});

const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    console.log(new TextDecoder().decode(value));
}
```

## Error Handling

All servers return appropriate HTTP status codes:

- **200**: Success
- **400**: Bad request (invalid parameters)
- **404**: Tool not found
- **500**: Internal server error

Error response format:
```json
{
    "detail": "Error message describing what went wrong"
}
```

## Docker Deployment

Start all servers with docker-compose:

```bash
cd backend/ai/mcp/servers
docker-compose up -d
```

Verify servers are running:

```bash
# Check all containers
docker-compose ps

# View logs
docker-compose logs -f sql-server
docker-compose logs -f google-drive-server
docker-compose logs -f sharepoint-server

# Stop all servers
docker-compose down
```

## Performance Considerations

1. **Connection Pooling**: Each server maintains a connection pool to its backend service
2. **Timeouts**: Configure appropriate timeouts for long-running queries
3. **Rate Limiting**: Consider implementing rate limiting in production
4. **Caching**: Results are not cached by default; implement as needed
5. **Compression**: Use gzip compression for large responses

## Security Considerations

1. **Network Isolation**: Servers run in a Docker network by default
2. **Environment Variables**: Sensitive credentials are passed via environment variables
3. **Input Validation**: All parameters are validated before execution
4. **SQL Injection**: Only SELECT queries are allowed; no DML operations
5. **SSL/TLS**: Consider adding SSL/TLS termination via reverse proxy (nginx, traefik)

## Troubleshooting

### Connection Refused
```bash
# Check if service is running
docker-compose ps

# Check service logs
docker-compose logs sql-server
```

### Tool Not Found
```bash
# List available tools
curl http://localhost:3001/tools
```

### Health Check Failing
```bash
# Direct health check
curl http://localhost:3001/health

# Check container logs
docker logs mcp-sql-server
```

### Database Connection Error
```bash
# Verify DATABASE_URL is correct
docker-compose exec sql-server env | grep DATABASE_URL

# Test connection manually
docker-compose exec sql-server python -c "from tools import SQLTools; t=SQLTools('DATABASE_URL'); print(t.show_tables())"
```

## Next Steps

1. Integrate HTTP clients with your MCP client applications
2. Configure reverse proxy (nginx/traefik) for SSL/TLS
3. Implement monitoring and logging
4. Set up rate limiting and access control
5. Deploy to production environment
