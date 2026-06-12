# MCP Servers Directory Structure

Comprehensive overview of the fastMcp-based server architecture.

```
backend/ai/mcp/servers/
│
├── 📄 README.md                      # Main documentation
├── 📄 STRUCTURE.md                   # This file
├── 📄 requirements.txt               # Master dependencies for all servers
├── 📄 docker-compose.yml             # Multi-service orchestration config
├── 📄 .env.example                   # Environment variable template
├── 📄 .gitignore                     # Git ignore patterns
├── 📄 Makefile                       # Convenience commands (Linux/Mac)
├── 🔧 start.sh                       # Startup script (Linux/Mac)
├── 🔧 start.bat                      # Startup script (Windows)
│
├── 📁 sql-server/                    # Universal SQL Database Server
│   ├── 📄 server.py                  # FastMcp application entry point
│   ├── 📄 tools.py                   # Database tools implementation
│   ├── 📄 requirements.txt           # SQL server dependencies
│   ├── 🐳 Dockerfile                # Container image definition
│   └── 📁 logs/                     # Server logs directory
│
├── 📁 google-drive-server/           # Google Drive Server
│   ├── 📄 server.py                  # FastMcp application entry point
│   ├── 📄 tools.py                   # Google Drive tools implementation
│   ├── 📄 requirements.txt           # GD server dependencies
│   ├── 🐳 Dockerfile                # Container image definition
│   └── 📁 logs/                     # Server logs directory
│
├── 📁 sharepoint-server/             # SharePoint Online Server
│   ├── 📄 server.py                  # FastMcp application entry point
│   ├── 📄 tools.py                   # SharePoint tools implementation
│   ├── 📄 requirements.txt           # SharePoint server dependencies
│   ├── 🐳 Dockerfile                # Container image definition
│   └── 📁 logs/                     # Server logs directory
│
└── 📁 secrets/                       # Credentials & API keys (git-ignored)
    ├── google-service-account.json   # Google Cloud service account
    └── sharepoint-credentials.json   # SharePoint OAuth credentials (optional)
```

## 📊 Server Architecture

### SQL Server (`sql-server/`)

**Purpose:** Universal connector for PostgreSQL, MySQL, and Oracle databases

**Files:**
- `server.py` - Main fastMcp server with 5 registered tools
- `tools.py` - Database operations via SQLAlchemy
- `requirements.txt` - Dependencies: sqlalchemy, database drivers
- `Dockerfile` - Python 3.11-slim base image

**Environment Variables:**
```
DATABASE_URL=postgresql://user:pass@host/dbname
```

**Key Tools:**
- `show_tables()` - List all database tables
- `show_table_schema(table_name)` - Get table structure
- `query_database(sql_query, limit)` - Execute SELECT queries
- `get_table_row_count(table_name)` - Get row counts
- `get_table_indexes(table_name)` - List table indexes

---

### Google Drive Server (`google-drive-server/`)

**Purpose:** File browsing, searching, and metadata retrieval for Google Drive

**Files:**
- `server.py` - Main fastMcp server with 5 registered tools
- `tools.py` - Google Drive API interactions
- `requirements.txt` - Dependencies: google-api-python-client, oauth2
- `Dockerfile` - Python 3.11-slim base image

**Environment Variables:**
```
GOOGLE_SERVICE_ACCOUNT_JSON=/secrets/google-service-account.json
```

**Key Tools:**
- `list_documents(parent_id, max_results)` - List files
- `list_folders(parent_id, max_results)` - List folders
- `get_file_info(file_id)` - Get file metadata
- `search_files(query, max_results)` - Search by name
- `get_folder_tree(folder_id, max_depth)` - Get hierarchy

---

### SharePoint Server (`sharepoint-server/`)

**Purpose:** File management in SharePoint Online with versioning support

**Files:**
- `server.py` - Main fastMcp server with 8 registered tools
- `tools.py` - SharePoint REST API interactions
- `requirements.txt` - Dependencies: office365-rest-python-client
- `Dockerfile` - Python 3.11-slim base image

**Environment Variables:**
```
SHAREPOINT_SITE_URL=https://tenant.sharepoint.com/sites/site
SHAREPOINT_CLIENT_ID=client-id-here
SHAREPOINT_CLIENT_SECRET=client-secret-here
```

**Key Tools:**
- `search_files(query, max_results)` - Search files
- `get_file(file_path)` - Download/read file
- `upload_file(library, path, content)` - Upload file
- `delete_file(file_path)` - Delete file
- `move_file(source, destination)` - Move file
- `copy_file(source, destination)` - Copy file
- `get_file_versions(file_path)` - Version history
- `restore_file_version(file_path, version_id)` - Restore version

---

## 🔄 Orchestration

### Docker Compose (`docker-compose.yml`)

Manages all services with networking and persistence:

**Services:**
- `sql-server` - Port 3001, depends on postgres
- `google-drive-server` - Port 3002
- `sharepoint-server` - Port 3003
- `postgres` - Database, port 5432 (optional)

**Networks:**
- `mcp-network` - Bridge network for inter-service communication

**Volumes:**
- `postgres_data` - PostgreSQL data persistence
- Per-server `logs/` directories for logging

---

## 🔐 Secrets Management

### Directory: `secrets/`

**Files (git-ignored):**
```
google-service-account.json
sharepoint-credentials.json (optional)
```

**Access in containers:**
- Mounted as read-only volumes
- Google Drive: `/secrets/google-service-account.json`
- SharePoint: Read from environment variables

---

## 📦 Dependencies

### Master Requirements (`requirements.txt`)

```
# Core
fastmcp>=0.0.1
python-dotenv>=1.0.0

# SQL
sqlalchemy>=2.0.0
psycopg2-binary, mysql-connector-python, cx_Oracle

# Google Drive
google-auth-oauthlib, google-api-python-client

# SharePoint
office365-rest-python-client

# Development (optional)
pytest, black, flake8, mypy
```

### Per-Server Requirements

Each server has its own `requirements.txt` with only necessary dependencies.

---

## 🐳 Docker Images

### Build & Registry

```bash
# Build all images
docker-compose build

# Built images:
- bugmentor_sql-server:latest
- bugmentor_google-drive-server:latest
- bugmentor_sharepoint-server:latest
- postgres:15-alpine (base image)
```

### Image Sizes

```
python:3.11-slim    ~140MB (base)
+ dependencies      ~50-100MB per server
Total per image     ~200-250MB
```

---

## 📝 Configuration Files

### `.env.example`

Template with all required environment variables:
```bash
# SQL
DATABASE_URL=postgresql://...

# Google Drive
GOOGLE_SERVICE_ACCOUNT_PATH=./secrets/...

# SharePoint
SHAREPOINT_SITE_URL=https://...
SHAREPOINT_CLIENT_ID=...
SHAREPOINT_CLIENT_SECRET=...

# Docker
DB_USER=postgres
DB_PASSWORD=...
DB_NAME=bugmentor
```

### `docker-compose.yml`

Service definitions:
- Container configuration
- Environment variables
- Port mappings
- Volume mounts
- Health checks
- Restart policies
- Logging configuration

### `Dockerfile` (per server)

Container recipe:
- Base image: `python:3.11-slim`
- Working directory: `/app`
- Dependencies installation
- Code copy
- Health check
- Startup command

---

## 🧰 Management Scripts

### Makefile (Linux/Mac)

```bash
make help          # Show all commands
make setup         # Initial setup
make build         # Build images
make up            # Start services
make down          # Stop services
make logs          # View logs
make test          # Run tests
```

### start.sh (Linux/Mac)

```bash
./start.sh setup
./start.sh build
./start.sh start
./start.sh logs [service]
./start.sh shell [service]
./start.sh clean
```

### start.bat (Windows)

```bash
start.bat setup
start.bat build
start.bat start
start.bat logs [service]
start.bat shell [service]
start.bat clean
```

---

## 📊 Data Flow

```
Client/AI Application
    │
    ├─→ SQL Server (stdio) ─→ SQLAlchemy ─→ Database
    │
    ├─→ Google Drive Server (stdio) ─→ Google API ─→ Google Drive
    │
    └─→ SharePoint Server (stdio) ─→ SharePoint REST API ─→ SharePoint
```

---

## 🔗 Communication Protocols

**Transport:** Stdio (Standard I/O)

**Port Mapping (Docker Compose):**
- SQL: localhost:3001 → container:3001
- Google Drive: localhost:3002 → container:3002
- SharePoint: localhost:3003 → container:3003

**Network (Docker):**
- Services communicate via `mcp-network` bridge
- Service discovery by container name

---

## 📚 Development Workflow

### Adding a New Tool

1. Add method to `tools.py` class:
```python
def my_tool(self, param: str) -> dict:
    """Tool description"""
    return {"status": "success", "result": ...}
```

2. Register in `server.py`:
```python
@app.tool()
def my_tool(param: str) -> dict:
    """Tool description"""
    return tools.my_tool(param)
```

3. Test locally before Docker deployment

### Adding a New Server

1. Create directory: `mkdir new-server`
2. Copy structure from existing server
3. Modify `tools.py` and `server.py`
4. Add to `docker-compose.yml`
5. Update documentation

---

## 🔍 Debugging

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sql-server

# Follow and filter
docker-compose logs -f | grep ERROR
```

### Shell Access

```bash
# Connect to running container
docker-compose exec sql-server /bin/bash

# Run single command
docker-compose exec sql-server python -c "..."
```

### Health Checks

```bash
# View health status
docker-compose ps

# Manual health check
docker-compose exec sql-server python healthcheck.py
```

---

## 📋 Maintenance

### Cleanup

```bash
# Remove stopped containers
docker-compose down

# Remove unused images/volumes
docker system prune

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

### Updates

```bash
# Rebuild images
docker-compose build --no-cache

# Update dependencies
pip-compile requirements.txt
```

### Backups

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres < backup.sql
```

---

## 📞 Support & References

- **fastMcp:** https://github.com/jloads/fastmcp
- **Docker:** https://docs.docker.com
- **SQLAlchemy:** https://docs.sqlalchemy.org
- **Google Drive API:** https://developers.google.com/drive
- **SharePoint REST:** https://learn.microsoft.com/sharepoint

---

## 📄 License

Part of BugMentor Project
