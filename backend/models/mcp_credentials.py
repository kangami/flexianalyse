"""
Multi-Tenant MCP Credentials Model

Stores encrypted credentials for each user's connectors.
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from config.db import Base


class MCPCredentials(Base):
    """
    Stores encrypted credentials for user connectors.
    Each user can have multiple credentials for different connectors.
    """
    
    __tablename__ = 'mcp_credentials'
    __table_args__ = (
        {'schema': 'public'},
    )
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False, index=True)
    
    # Connector type: 'sql', 'google_drive', 'sharepoint'
    connector_type = Column(String(50), nullable=False, index=True)
    
    # Encrypted credentials JSON (stored as encrypted string)
    encrypted_credentials = Column(Text, nullable=False)
    
    # Connector-specific metadata
    sql_database_type = Column(String(20), nullable=True)  # 'postgresql', 'mysql', 'oracle'
    sql_host = Column(String(255), nullable=True)
    sql_database_name = Column(String(255), nullable=True)
    
    google_drive_workspace_id = Column(String(255), nullable=True)
    google_drive_service_account_email = Column(String(255), nullable=True)
    
    sharepoint_site_url = Column(String(500), nullable=True)
    sharepoint_tenant_id = Column(String(255), nullable=True)
    
    # Status and tracking
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)  # Credentials tested and working
    last_verified_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Relationships
    user = relationship("User", backref="mcp_credentials")
    organization = relationship("Organization", backref="mcp_credentials")
    
    def __repr__(self):
        return f"<MCPCredentials {self.connector_type}:{self.user_id}>"
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None


class MCPServerInstance(Base):
    """
    Tracks active MCP server instances per user/tenant.
    Used for lifecycle management and health monitoring.
    """
    
    __tablename__ = 'mcp_server_instances'
    __table_args__ = (
        {'schema': 'public'},
    )
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant identification
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, unique=True, index=True)  # org_id:user_id
    
    # Server configuration
    connector_type = Column(String(50), nullable=False)  # 'sql', 'google_drive', 'sharepoint'
    http_port = Column(Integer, nullable=False, unique=True)
    http_host = Column(String(50), default='127.0.0.1')
    
    # Process management
    process_id = Column(Integer, nullable=True)
    container_id = Column(String(255), nullable=True)  # Docker container ID if containerized
    
    # Status
    status = Column(String(20), default='stopped')  # 'running', 'stopped', 'error', 'restarting'
    status_message = Column(String(500), nullable=True)
    
    # Health
    is_healthy = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    # Audit
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="mcp_server_instances")
    organization = relationship("Organization", backref="mcp_server_instances")
    
    def __repr__(self):
        return f"<MCPServerInstance {self.tenant_id}:{self.connector_type}>"
