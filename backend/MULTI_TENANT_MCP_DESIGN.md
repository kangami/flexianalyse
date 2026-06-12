# Multi-Tenant MCP Architecture

## Overview

This document describes the multi-tenant architecture for MCP servers where each user/organization has dedicated server instances with isolated credentials.

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Backend                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  User/Organization Identification (JWT/Session)      │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MCP Orchestrator Service                            │  │
│  │  • Manages user/org credentials                      │  │
│  │  • Spins up dedicated server instances               │  │
│  │  • Allocates ports dynamically                       │  │
│  │  • Manages server lifecycle                          │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↓              ↓              ↓                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │User 1 Tenant │  │User 2 Tenant │  │User N Tenant │     │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤     │
│  │SQL:3001      │  │SQL:3011      │  │SQL:3021      │     │
│  │GDrive:3002   │  │GDrive:3012   │  │GDrive:3022   │     │
│  │SP:3003       │  │SP:3013       │  │SP:3023       │     │
│  │              │  │              │  │              │     │
│  │Creds:User1   │  │Creds:User2   │  │Creds:UserN   │     │
│  │DB:Schema1    │  │DB:Schema2    │  │DB:SchemaN    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. MCP Orchestrator Service
Central service managing all user-specific MCP instances.

**Responsibilities:**
- ✅ User/Organization identification
- ✅ Credential management (encrypted storage)
- ✅ Server lifecycle management (start/stop/restart)
- ✅ Port allocation and tracking
- ✅ Database/schema isolation

**Location:** `backend/services/mcp_orchestrator.py`

### 2. Credential Management System
Secure storage and injection of per-user credentials.

**Features:**
- ✅ Encrypted credential storage in database
- ✅ Per-connector credential configuration
- ✅ Credential validation before server startup
- ✅ Rotation and expiration handling

**Location:** `backend/models/mcp_credentials.py`

### 3. User-Specific MCP Clients
Each user gets dedicated client instances pointing to their servers.

**Connector → MCP Client Mapping:**

Each credential/connector maps to its own MCP client. This enables:
- Multiple databases per user (production, analytics, staging)
- Multiple Google Drive service accounts per user
- Multiple SharePoint tenants per user
- Flexible credential management

```python
# User has 2 SQL databases
Connector 1: postgresql://prod.example.com/users → SQLServerClient(port:3100)
Connector 2: mysql://analytics.example.com/data → SQLServerClient(port:3100)

# User specifies which connector to use for the query
POST /api/mcp/database/query
{
    "connector_id": "550e8400...",  # Use Connector 1
    "sql_query": "SELECT * FROM users"
}
```

**Pattern:**
```python
# Get client for specific connector
connector_client = await MCPClientFactory.get_client_for_connector(
    connector_id="550e8400-e29b-41d4-a716-446655440000",
    user_id=user1_id,
    org_id=org_a
)
# Returns ConnectorClient with:
# - .connector_id: The specific credential ID
# - .connector_type: 'sql', 'google_drive', etc.
# - .client: The actual MCP client instance
# - .port: The port this client connects to
```

## Key Architectural Improvement: Connector → Client Mapping

**Before:** Generic clients per user
```
User1.sql_client → queries ANY database with User1's default credentials
User2.sql_client → queries ANY database with User2's default credentials
```

**After:** Connector-specific clients
```
User1.Connector_1 (PostgreSQL prod) → SQLServerClient(port:3100)
User1.Connector_2 (MySQL analytics) → SQLServerClient(port:3100)
User1.Connector_3 (Google Drive) → GoogleDriveClient(port:3101)

Query specifies: "Use Connector_2" → Routes to MySQL analytics DB with correct credentials
```

**Benefits:**
✅ Support multiple databases per user (prod, staging, analytics)  
✅ Support multiple Google Drive accounts per user  
✅ Support multiple SharePoint tenants per user  
✅ Fine-grained credential management  
✅ Each connector has its own credentials encrypted separately  
✅ Easy to rotate or revoke specific connectors  
✅ Audit trail per connector  

---



**Options:**
- **Schema Isolation**: Single PostgreSQL, separate schema per user
- **Database Isolation**: Separate database per organization/user
- **Row-Level Security**: Single schema with RLS policies per user

## Implementation Details

### Component 1: Credential Model

```python
# backend/models/mcp_credentials.py

from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

class MCPCredentials(Base):
    __tablename__ = 'mcp_credentials'
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    organization_id = Column(UUID, ForeignKey('organizations.id'), nullable=False)
    
    connector_type = Column(String(50), nullable=False)  # 'sql', 'google_drive', 'sharepoint'
    
    # Encrypted credentials JSON
    encrypted_credentials = Column(String, nullable=False)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    
    # Credential specifics (examples)
    sql_database_type = Column(String(20), nullable=True)  # postgresql, mysql, oracle
    google_drive_workspace = Column(String, nullable=True)
    sharepoint_site_url = Column(String, nullable=True)
    
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
```

### Component 2: MCP Orchestrator Service

```python
# backend/services/mcp_orchestrator.py

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import asyncio
import logging
from encryption_service import EncryptionService
from mcp_credentials_repo import MCPCredentialsRepository

@dataclass
class TenantServerConfig:
    """Configuration for a tenant's MCP servers"""
    tenant_id: str
    user_id: str
    sql_port: int
    google_drive_port: int
    sharepoint_port: int
    process_ids: Dict[str, int]
    status: str  # 'running', 'stopped', 'error'
    created_at: datetime

class MCPOrchestrator:
    """
    Manages dedicated MCP server instances per user/tenant
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_tenants: Dict[str, TenantServerConfig] = {}
        self.port_pool = PortPoolManager(start_port=3001, max_tenants=1000)
        self.encryption_service = EncryptionService()
        self.credentials_repo = MCPCredentialsRepository()
    
    async def setup_tenant_servers(
        self, 
        user_id: str, 
        org_id: str,
        connector_credentials: Dict[str, dict]
    ) -> TenantServerConfig:
        """
        Set up dedicated MCP servers for a user/tenant
        
        Args:
            user_id: User identifier
            org_id: Organization identifier
            connector_credentials: {
                'sql': {'database_url': '...'},
                'google_drive': {'service_account': '...'},
                'sharepoint': {'site_url': '...', 'client_id': '...', 'client_secret': '...'}
            }
        
        Returns:
            TenantServerConfig with server details and ports
        """
        tenant_id = f"{org_id}:{user_id}"
        
        # Check if servers already running
        if tenant_id in self.active_tenants:
            return self.active_tenants[tenant_id]
        
        self.logger.info(f"Setting up MCP servers for tenant {tenant_id}")
        
        # Allocate ports
        sql_port, gd_port, sp_port = self.port_pool.allocate_ports()
        
        # Store credentials (encrypted)
        await self._store_credentials(user_id, org_id, connector_credentials)
        
        # Spin up servers
        process_ids = await self._start_tenant_servers(
            tenant_id,
            sql_port,
            gd_port,
            sp_port,
            connector_credentials
        )
        
        config = TenantServerConfig(
            tenant_id=tenant_id,
            user_id=user_id,
            sql_port=sql_port,
            google_drive_port=gd_port,
            sharepoint_port=sp_port,
            process_ids=process_ids,
            status='running',
            created_at=datetime.utcnow()
        )
        
        self.active_tenants[tenant_id] = config
        self.logger.info(f"✓ MCP servers started for {tenant_id}")
        
        return config
    
    async def _start_tenant_servers(
        self,
        tenant_id: str,
        sql_port: int,
        gd_port: int,
        sp_port: int,
        credentials: Dict[str, dict]
    ) -> Dict[str, int]:
        """Start individual server instances for tenant"""
        
        process_ids = {}
        
        # Start SQL Server
        if 'sql' in credentials:
            pid = await self._start_server(
                'sql-server',
                tenant_id,
                sql_port,
                credentials['sql']
            )
            process_ids['sql'] = pid
        
        # Start Google Drive Server
        if 'google_drive' in credentials:
            pid = await self._start_server(
                'google-drive-server',
                tenant_id,
                gd_port,
                credentials['google_drive']
            )
            process_ids['google_drive'] = pid
        
        # Start SharePoint Server
        if 'sharepoint' in credentials:
            pid = await self._start_server(
                'sharepoint-server',
                tenant_id,
                sp_port,
                credentials['sharepoint']
            )
            process_ids['sharepoint'] = pid
        
        return process_ids
    
    async def _start_server(
        self,
        server_type: str,
        tenant_id: str,
        port: int,
        credentials: dict
    ) -> int:
        """Start a single MCP server with tenant isolation"""
        
        env_vars = {
            'HTTP_HOST': '127.0.0.1',
            'HTTP_PORT': str(port),
            'TENANT_ID': tenant_id,
            'LOG_FILE': f'/var/log/mcp/{tenant_id}-{server_type}.log'
        }
        
        # Inject connector-specific credentials
        if server_type == 'sql-server':
            env_vars['DATABASE_URL'] = credentials.get('database_url')
        
        elif server_type == 'google-drive-server':
            # Save service account to temp encrypted file
            sa_path = await self._create_temp_credential_file(
                tenant_id,
                'google-drive',
                credentials.get('service_account')
            )
            env_vars['GOOGLE_SERVICE_ACCOUNT_JSON'] = sa_path
        
        elif server_type == 'sharepoint-server':
            env_vars['SHAREPOINT_SITE_URL'] = credentials.get('site_url')
            env_vars['SHAREPOINT_CLIENT_ID'] = credentials.get('client_id')
            env_vars['SHAREPOINT_CLIENT_SECRET'] = credentials.get('client_secret')
        
        # Start process (Docker container or direct Python)
        pid = await self._spawn_server_process(server_type, env_vars)
        
        return pid
    
    async def _store_credentials(
        self,
        user_id: str,
        org_id: str,
        connector_credentials: Dict[str, dict]
    ):
        """Store encrypted credentials in database"""
        
        for connector_type, creds in connector_credentials.items():
            encrypted = self.encryption_service.encrypt(creds)
            
            credential_obj = MCPCredentials(
                user_id=user_id,
                organization_id=org_id,
                connector_type=connector_type,
                encrypted_credentials=encrypted
            )
            
            await self.credentials_repo.create(credential_obj)
    
    async def get_tenant_config(
        self,
        user_id: str,
        org_id: str
    ) -> Optional[TenantServerConfig]:
        """Get configuration for existing tenant servers"""
        
        tenant_id = f"{org_id}:{user_id}"
        
        if tenant_id in self.active_tenants:
            config = self.active_tenants[tenant_id]
            
            # Check if servers are still healthy
            if await self._check_tenant_health(tenant_id):
                return config
            else:
                # Servers crashed, need restart
                await self.restart_tenant_servers(user_id, org_id)
                return self.active_tenants.get(tenant_id)
        
        return None
    
    async def stop_tenant_servers(
        self,
        user_id: str,
        org_id: str
    ):
        """Stop all servers for a tenant"""
        
        tenant_id = f"{org_id}:{user_id}"
        
        if tenant_id not in self.active_tenants:
            return
        
        config = self.active_tenants[tenant_id]
        
        # Kill processes
        for server_type, pid in config.process_ids.items():
            await self._kill_server_process(pid)
        
        # Free ports
        self.port_pool.release_ports(
            config.sql_port,
            config.google_drive_port,
            config.sharepoint_port
        )
        
        # Remove from active
        del self.active_tenants[tenant_id]
        
        self.logger.info(f"✓ Stopped MCP servers for {tenant_id}")
    
    async def restart_tenant_servers(
        self,
        user_id: str,
        org_id: str
    ):
        """Restart all servers for a tenant"""
        
        # Get stored credentials
        credentials = await self.credentials_repo.get_by_user_and_org(
            user_id, org_id
        )
        
        # Convert stored credentials back to dict
        connector_credentials = {}
        for cred_obj in credentials:
            decrypted = self.encryption_service.decrypt(cred_obj.encrypted_credentials)
            connector_credentials[cred_obj.connector_type] = decrypted
        
        # Stop old servers
        await self.stop_tenant_servers(user_id, org_id)
        
        # Start new servers
        return await self.setup_tenant_servers(
            user_id, org_id, connector_credentials
        )
    
    async def _check_tenant_health(self, tenant_id: str) -> bool:
        """Check health of all servers for a tenant"""
        
        config = self.active_tenants.get(tenant_id)
        if not config:
            return False
        
        try:
            # Check each server
            sql_healthy = await self._health_check(config.sql_port)
            gd_healthy = await self._health_check(config.google_drive_port)
            sp_healthy = await self._health_check(config.sharepoint_port)
            
            return sql_healthy and gd_healthy and sp_healthy
        
        except Exception as e:
            self.logger.error(f"Health check failed for {tenant_id}: {e}")
            return False
    
    async def _health_check(self, port: int) -> bool:
        """Check if server is responding"""
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                return response.status_code == 200
        except:
            return False


class PortPoolManager:
    """Manages port allocation for tenant servers"""
    
    def __init__(self, start_port: int = 3001, max_tenants: int = 1000):
        self.start_port = start_port
        self.max_tenants = max_tenants
        self.allocated_ranges: Dict[int, Tuple[int, int, int]] = {}
        self.next_tenant_index = 0
    
    def allocate_ports(self) -> Tuple[int, int, int]:
        """Allocate 3 consecutive ports for a tenant"""
        
        if self.next_tenant_index >= self.max_tenants:
            raise RuntimeError("Maximum number of tenants reached")
        
        base_port = self.start_port + (self.next_tenant_index * 10)
        tenant_id = self.next_tenant_index
        
        ports = (base_port, base_port + 1, base_port + 2)
        self.allocated_ranges[tenant_id] = ports
        
        self.next_tenant_index += 1
        
        return ports
    
    def release_ports(self, sql_port: int, gd_port: int, sp_port: int):
        """Release ports back to pool for reuse"""
        
        for tenant_id, (s, g, sp) in list(self.allocated_ranges.items()):
            if s == sql_port and g == gd_port and sp == sp_port:
                del self.allocated_ranges[tenant_id]
                break
```

### Component 3: MCP Client Factory

```python
# backend/services/mcp_client_factory.py

from typing import Optional
from mcp_orchestrator import MCPOrchestrator
from example_client import (
    SQLServerClient,
    GoogleDriveServerClient,
    SharePointServerClient
)

@dataclass
class UserMCPClients:
    """Container for user-specific MCP clients"""
    sql: SQLServerClient
    google_drive: GoogleDriveServerClient
    sharepoint: SharePointServerClient
    user_id: str
    org_id: str

class MCPClientFactory:
    """Factory for creating user-specific MCP clients"""
    
    def __init__(self, orchestrator: MCPOrchestrator):
        self.orchestrator = orchestrator
    
    async def get_clients(
        self,
        user_id: str,
        org_id: str
    ) -> UserMCPClients:
        """
        Get dedicated MCP clients for a user
        
        Automatically:
        1. Checks if tenant servers exist
        2. Starts them if needed
        3. Returns clients pointing to user's servers
        """
        
        # Ensure tenant servers are running
        config = await self.orchestrator.get_tenant_config(user_id, org_id)
        
        if not config:
            # Credentials should already be stored
            config = await self.orchestrator.setup_tenant_servers(
                user_id,
                org_id,
                connector_credentials={}  # Load from database
            )
        
        # Create user-specific clients
        clients = UserMCPClients(
            sql=SQLServerClient(f"http://127.0.0.1:{config.sql_port}"),
            google_drive=GoogleDriveServerClient(f"http://127.0.0.1:{config.google_drive_port}"),
            sharepoint=SharePointServerClient(f"http://127.0.0.1:{config.sharepoint_port}"),
            user_id=user_id,
            org_id=org_id
        )
        
        return clients
```

### Component 4: Integration in Controllers

```python
# backend/controllers/connector_controller.py

from flask import request
from mcp_orchestrator import MCPOrchestrator
from mcp_client_factory import MCPClientFactory
from decorators import require_auth

orchestrator = MCPOrchestrator()
client_factory = MCPClientFactory(orchestrator)

@app.route('/api/connectors/setup', methods=['POST'])
@require_auth
async def setup_connector():
    """Setup connector credentials for current user"""
    
    user_id = request.user.id
    org_id = request.user.organization_id
    
    data = request.json
    connector_type = data.get('type')  # 'sql', 'google_drive', 'sharepoint'
    credentials = data.get('credentials')
    
    # Store credentials
    orchestrator.store_credentials(user_id, org_id, {
        connector_type: credentials
    })
    
    # Setup servers
    config = await orchestrator.setup_tenant_servers(
        user_id,
        org_id,
        {connector_type: credentials}
    )
    
    return {
        'status': 'success',
        'config': {
            'tenant_id': config.tenant_id,
            'ports': {
                'sql': config.sql_port,
                'google_drive': config.google_drive_port,
                'sharepoint': config.sharepoint_port
            }
        }
    }

@app.route('/api/database/query', methods=['POST'])
@require_auth
async def query_database():
    """Execute query on user's dedicated SQL server"""
    
    user_id = request.user.id
    org_id = request.user.organization_id
    
    # Get user-specific clients
    clients = await client_factory.get_clients(user_id, org_id)
    
    # Execute query on user's SQL server
    result = await clients.sql.query_database(
        request.json.get('sql_query'),
        limit=request.json.get('limit', 1000)
    )
    
    return result
```

## Isolation Guarantees

### 1. Credential Isolation
- ✅ Each user's credentials encrypted and stored separately
- ✅ Credentials injected only to that user's server instance
- ✅ No credential sharing between tenants

### 2. Network Isolation
- ✅ Each tenant's servers listen on different ports (127.0.0.1 only)
- ✅ Servers accessible only through authenticated backend
- ✅ No direct cross-tenant communication

### 3. Process Isolation
- ✅ Separate Python process per tenant
- ✅ Separate resource allocation (Docker constraints)
- ✅ Separate logging per tenant

### 4. Data Isolation
- ✅ Database schema per user/org
- ✅ Query results only for that user's credentials
- ✅ No data leakage between tenants

### 5. Authentication Isolation
- ✅ JWT tokens tied to user_id + org_id
- ✅ Backend validates user before allowing client access
- ✅ Audit logging of all cross-tenant access attempts

## Multi-Tenant Data Flow

```
1. User Login
   ↓
   Backend generates JWT with user_id + org_id
   
2. User submits query
   ↓
   Backend verifies JWT
   ↓
   Extracts user_id + org_id
   
3. Client Factory gets user-specific clients
   ↓
   MCPOrchestrator ensures tenant servers running
   ↓
   Returns clients pointing to user's servers (127.0.0.1:300X)
   
4. Query execution
   ↓
   User's SQL server (isolated process)
   ↓
   Uses user's DATABASE_URL credentials
   ↓
   Results returned only to authenticated user
```

## Configuration per Tenant

Each tenant's configuration:

```python
{
    "tenant_id": "org123:user456",
    "servers": {
        "sql": {
            "port": 3001,
            "pid": 12345,
            "credentials": "database_url (encrypted)"
        },
        "google_drive": {
            "port": 3002,
            "pid": 12346,
            "credentials": "service_account_json (encrypted)"
        },
        "sharepoint": {
            "port": 3003,
            "pid": 12347,
            "credentials": "client_id/secret (encrypted)"
        }
    },
    "created_at": "2026-06-05T10:00:00Z",
    "status": "running"
}
```

## Benefits

✅ **True Multi-Tenancy**: Each user has isolated servers  
✅ **Credential Security**: No credential sharing, encrypted storage  
✅ **Resource Isolation**: Per-tenant resource allocation  
✅ **Scalability**: Can run thousands of tenant servers  
✅ **Audit Trail**: Track per-tenant access and operations  
✅ **Graceful Degradation**: One tenant's crash doesn't affect others  
✅ **Easy Onboarding**: Auto-provision on first connector setup  
✅ **Flexible Scaling**: Add/remove tenants dynamically  

## Deployment Considerations

### Resource Planning
- Each tenant needs: ~100MB RAM + credentials storage
- Plan for concurrent users * resource per tenant
- Use Docker resource limits per container

### Monitoring
- Per-tenant health checks
- Alert on server crashes
- Track resource usage per tenant

### Cleanup
- Stop unused tenant servers after inactivity
- Graceful shutdown on user deletion
- Credential cleanup

## Next Steps

1. Implement MCPCredentials model
2. Implement MCPOrchestrator service
3. Implement MCPClientFactory
4. Add credential management UI
5. Test multi-tenant isolation
6. Deploy with proper monitoring
