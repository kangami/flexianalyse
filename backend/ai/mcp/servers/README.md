# BugMentor MCP Servers

Professional Model Context Protocol (MCP) servers built with fastMcp for seamless integration with AI clients.

## 📦 Overview

Three dedicated MCP servers providing specialized tools with **HTTP streaming transport**:

- **SQL Server** (Port 3001) - Universal database connector (PostgreSQL, MySQL, Oracle)
- **Google Drive Server** (Port 3002) - File browsing and document management
- **SharePoint Server** (Port 3003) - SharePoint Online file operations and versioning

## 🏗️ Architecture

```
backend/ai/mcp/servers/
├── sql-server/              # SQL universal connector
│   ├── server.py           # FastMcp + FastAPI server entry point (HTTP on :3001)
│   ├── tools.py            # Database tools implementation
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Container image
├── google-drive-server/    # Google Drive file manager
│   ├── server.py           # FastMcp + FastAPI server entry point (HTTP on :3002)
│   ├── tools.py
│   ├── requirements.txt
│   └── Dockerfile
├── sharepoint-server/      # SharePoint file manager
│   ├── server.py           # FastMcp + FastAPI server entry point (HTTP on :3003)
│   ├── tools.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml      # Orchestration config with health checks
├── HTTP_STREAMING.md       # HTTP client documentation & examples
└── .env.example            # Configuration template
```

## 🔌 Transport Layer

**HTTP Streaming with FastAPI & Uvicorn**

All servers now communicate via HTTP streaming instead of stdio:

- ✅ **Scalable**: Multiple concurrent clients
- ✅ **Streamable**: Efficient large result set handling
- ✅ **REST API**: Standard HTTP methods for tool execution
- ✅ **Monitored**: Built-in health check endpoints (`/health`, `/info`, `/tools`)
- ✅ **Containerized**: Proper Docker port mapping (3001, 3002, 3003)

See [HTTP_STREAMING.md](./HTTP_STREAMING.md) for complete client documentation and examples.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Environment-specific credentials

### Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure credentials in `.env`:**
   ```bash
   # SQL Server
   DATABASE_URL=postgresql://user:password@postgres:5432/bugmentor
   
   # Google Drive
   GOOGLE_SERVICE_ACCOUNT_PATH=./secrets/google-service-account.json
   
   # SharePoint
   SHAREPOINT_SITE_URL=https://tenant.sharepoint.com/sites/sitename
   SHAREPOINT_CLIENT_ID=your-app-id
   SHAREPOINT_CLIENT_SECRET=your-app-secret
   ```

3. **Start all servers:**
   ```bash
   docker-compose up -d
   ```

4. **Verify servers are running:**
   ```bash
   docker-compose ps
   ```

## 📋 SQL Server

### Supported Databases

- **PostgreSQL** - `postgresql://user:password@host:5432/dbname`
- **MySQL** - `mysql+mysqlconnector://user:password@host:3306/dbname`
- **Oracle** - `oracle://user:password@host:1521/dbname`

### Available Tools

```python
# List all tables
show_tables()
→ {"status": "success", "tables": [...], "count": 5}

# Get table structure
show_table_schema(table_name="users")
→ {"status": "success", "schema": {...}}

# Execute SELECT queries
query_database(
    sql_query="SELECT * FROM users WHERE active = true",
    limit=1000
)
→ {"status": "success", "rows": [...], "columns": [...]}

# Get row count
get_table_row_count(table_name="users")
→ {"status": "success", "row_count": 150}

# List table indexes
get_table_indexes(table_name="users")
→ {"status": "success", "indexes": [...]}
```

### Docker Run (SQL)

```bash
docker run -d \
  -e DATABASE_URL="postgresql://postgres:password@postgres:5432/bugmentor" \
  -p 3001:3001 \
  --name mcp-sql-server \
  bugmentor-mcp-sql-server:latest
```

## 🔵 Google Drive Server

### Setup

1. **Create Google Cloud project & service account:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project
   - Enable Google Drive API
   - Create Service Account
   - Generate JSON key file

2. **Place credentials:**
   ```bash
   mkdir -p secrets
   cp google-service-account.json secrets/
   ```

### Available Tools

```python
# List documents in folder
list_documents(parent_id=None, max_results=50)
→ {"status": "success", "documents": [...], "count": 10}

# List folders
list_folders(parent_id=None, max_results=50)
→ {"status": "success", "folders": [...], "count": 5}

# Get file metadata
get_file_info(file_id="1abc123...")
→ {"status": "success", "file": {...}}

# Search files
search_files(query="financial report", max_results=20)
→ {"status": "success", "results": [...]}

# Get folder hierarchy
get_folder_tree(folder_id=None, max_depth=3)
→ {"status": "success", "items": [...]}
```

### Docker Run (Google Drive)

```bash
docker run -d \
  -e GOOGLE_SERVICE_ACCOUNT_JSON=/secrets/google-service-account.json \
  -v $(pwd)/secrets:/secrets:ro \
  -p 3002:3002 \
  --name mcp-google-drive-server \
  bugmentor-mcp-google-drive-server:latest
```

## 📄 SharePoint Server

### Setup

1. **Register Azure AD Application:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Azure Active Directory > App Registrations > New
   - Create credentials (Client ID & Secret)
   - Grant SharePoint API permissions

2. **Configure `.env`:**
   ```bash
   SHAREPOINT_SITE_URL=https://tenant.sharepoint.com/sites/yoursite
   SHAREPOINT_CLIENT_ID=your-client-id
   SHAREPOINT_CLIENT_SECRET=your-client-secret
   ```

### Available Tools

```python
# Search files
search_files(query="budget", max_results=50)
→ {"status": "success", "results": [...]}

# Get file content
get_file(file_path="/sites/site/Shared Documents/file.pdf")
→ {"status": "success", "file": {...}}

# Upload file
upload_file(
    library_name="Shared Documents",
    file_path="folder/myfile.txt",
    file_content=b"file content"
)
→ {"status": "success", "target_path": "..."}

# Delete file
delete_file(file_path="/sites/site/Shared Documents/file.pdf")
→ {"status": "success", "message": "File deleted"}

# Move file
move_file(
    source_path="/sites/site/Lib1/file.txt",
    destination_path="/sites/site/Lib2/file.txt"
)
→ {"status": "success", "message": "..."}

# Copy file
copy_file(
    source_path="/sites/site/Lib/file.txt",
    destination_path="/sites/site/Lib/file-copy.txt"
)
→ {"status": "success", "message": "..."}

# Get version history
get_file_versions(file_path="/sites/site/Lib/file.txt")
→ {"status": "success", "versions": [...]}

# Restore previous version
restore_file_version(file_path="/sites/site/Lib/file.txt", version_id=2)
→ {"status": "success", "message": "..."}
```

### Docker Run (SharePoint)

```bash
docker run -d \
  -e SHAREPOINT_SITE_URL="https://tenant.sharepoint.com/sites/site" \
  -e SHAREPOINT_CLIENT_ID="your-id" \
  -e SHAREPOINT_CLIENT_SECRET="your-secret" \
  -p 3003:3003 \
  --name mcp-sharepoint-server \
  bugmentor-mcp-sharepoint-server:latest
```

## 🐳 Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Access specific service logs
docker-compose logs sql-server
docker-compose logs google-drive-server
docker-compose logs sharepoint-server

# Execute command in container
docker-compose exec sql-server python -c "import sys; print(sys.version)"
```

## 📊 Network Configuration

Services communicate via the `mcp-network` bridge:

- **SQL Server** → `http://sql-server:3001`
- **Google Drive** → `http://google-drive-server:3002`
- **SharePoint** → `http://sharepoint-server:3003`
- **PostgreSQL** → `postgres:5432`

## 🔒 Security Considerations

1. **Credentials Management**
   - Use environment variables, never commit secrets
   - Mount credentials as read-only volumes
   - Rotate service account keys regularly

2. **Database Access**
   - Only SELECT queries allowed (write operations blocked)
   - Use connection pooling disabled for safety
   - Implement query result limiting (1000 rows default)

3. **API Authentication**
   - Service accounts for Google Drive
   - OAuth 2.0 for SharePoint
   - API keys never exposed in logs

## 🛠️ Development

### Local Setup (without Docker)

```bash
# SQL Server
cd sql-server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=postgresql://user:password@localhost:5432/db python server.py

# Google Drive Server
cd google-drive-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
GOOGLE_SERVICE_ACCOUNT_JSON=./secrets/account.json python server.py

# SharePoint Server
cd sharepoint-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
SHAREPOINT_SITE_URL=... SHAREPOINT_CLIENT_ID=... SHAREPOINT_CLIENT_SECRET=... python server.py
```

### Adding New Tools

1. Add method to `tools.py` class
2. Decorate with `@app.tool()` in `server.py`
3. Document parameters and return values
4. Test with fastMcp client

## 📝 Logging

All services log to:
- **Console** - Real-time output
- **File** - `{service}/logs/*.log`
- **Docker** - JSON format with rotation

View logs:
```bash
docker-compose logs -f --tail=100
```

## 🐛 Troubleshooting

### SQL Server won't connect
```bash
# Check database connectivity
docker-compose exec sql-server python -c "
from tools import SQLTools
from os import getenv
SQLTools(getenv('DATABASE_URL'))
"
```

### Google Drive auth fails
```bash
# Verify service account JSON
docker-compose exec google-drive-server python -c "
import json
with open('/secrets/google-service-account.json') as f:
    print(json.load(f).keys())
"
```

### SharePoint timeout
```bash
# Check network connectivity
docker-compose exec sharepoint-server ping sharepoint.com
```

## 📚 References

- [FastMcp Documentation](https://github.com/jloads/fastmcp)
- [MCP Specification](https://modelcontextprotocol.io)
- [Google Drive API](https://developers.google.com/drive)
- [SharePoint REST API](https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/get-to-know-the-sharepoint-rest-service)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org)

## 📞 Support

For issues and questions:
1. Check logs: `docker-compose logs`
2. Verify environment configuration
3. Ensure all dependencies installed
4. Check API rate limits and quotas

## 📄 License

Part of BugMentor project
