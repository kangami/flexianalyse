"""
MCP Credentials Repository

Handles database operations for storing and retrieving user credentials.
"""

import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.mcp_credentials import MCPCredentials, MCPServerInstance
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MCPCredentialsRepository(BaseRepository):
    """Repository for managing MCP credentials"""
    
    model = MCPCredentials
    
    async def get_by_user_and_org(
        self,
        session: AsyncSession,
        user_id: UUID,
        org_id: UUID,
        connector_type: Optional[str] = None
    ) -> List[MCPCredentials]:
        """
        Get credentials for a user/org, optionally filtered by connector type
        
        Args:
            session: AsyncSession
            user_id: User UUID
            org_id: Organization UUID
            connector_type: Optional filter by connector type
        
        Returns:
            List of MCPCredentials
        """
        
        query = select(MCPCredentials).where(
            and_(
                MCPCredentials.user_id == user_id,
                MCPCredentials.organization_id == org_id,
                MCPCredentials.deleted_at.is_(None),
                MCPCredentials.is_active == True
            )
        )
        
        if connector_type:
            query = query.where(MCPCredentials.connector_type == connector_type)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_id(
        self,
        session: AsyncSession,
        credential_id: UUID
    ) -> Optional[MCPCredentials]:
        """Get credential by ID"""
        
        query = select(MCPCredentials).where(
            and_(
                MCPCredentials.id == credential_id,
                MCPCredentials.deleted_at.is_(None)
            )
        )
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_by_user(
        self,
        session: AsyncSession,
        user_id: UUID
    ) -> List[MCPCredentials]:
        """Get all active credentials for a user across organizations"""
        
        query = select(MCPCredentials).where(
            and_(
                MCPCredentials.user_id == user_id,
                MCPCredentials.is_active == True,
                MCPCredentials.deleted_at.is_(None)
            )
        )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def soft_delete(
        self,
        session: AsyncSession,
        credential_id: UUID
    ) -> bool:
        """Soft delete a credential"""
        
        credential = await self.get_by_id(session, credential_id)
        if not credential:
            return False
        
        from datetime import datetime
        credential.deleted_at = datetime.utcnow()
        await session.commit()
        
        logger.info(f"Soft deleted credential {credential_id}")
        return True
    
    async def mark_verified(
        self,
        session: AsyncSession,
        credential_id: UUID
    ):
        """Mark credential as verified"""
        
        from datetime import datetime
        
        credential = await self.get_by_id(session, credential_id)
        if credential:
            credential.is_verified = True
            credential.last_verified_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Marked credential {credential_id} as verified")


class MCPServerInstanceRepository(BaseRepository):
    """Repository for managing MCP server instances"""
    
    model = MCPServerInstance
    
    async def get_by_tenant_id(
        self,
        session: AsyncSession,
        tenant_id: str
    ) -> List[MCPServerInstance]:
        """Get all server instances for a tenant"""
        
        query = select(MCPServerInstance).where(
            MCPServerInstance.tenant_id == tenant_id
        )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_tenant_and_connector(
        self,
        session: AsyncSession,
        tenant_id: str,
        connector_type: str
    ) -> Optional[MCPServerInstance]:
        """Get server instance for a specific connector"""
        
        query = select(MCPServerInstance).where(
            and_(
                MCPServerInstance.tenant_id == tenant_id,
                MCPServerInstance.connector_type == connector_type
            )
        )
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_instances(
        self,
        session: AsyncSession
    ) -> List[MCPServerInstance]:
        """Get all running server instances"""
        
        query = select(MCPServerInstance).where(
            MCPServerInstance.status == 'running'
        )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self,
        session: AsyncSession,
        instance_id: UUID,
        status: str,
        message: Optional[str] = None
    ):
        """Update server instance status"""
        
        instance = await self.get_by_id(session, instance_id)
        if instance:
            from datetime import datetime
            instance.status = status
            if message:
                instance.status_message = message
            instance.updated_at = datetime.utcnow()
            await session.commit()
    
    async def record_health_check(
        self,
        session: AsyncSession,
        instance_id: UUID,
        is_healthy: bool
    ):
        """Record health check result"""
        
        from datetime import datetime
        
        instance = await self.get_by_id(session, instance_id)
        if instance:
            instance.is_healthy = is_healthy
            instance.last_health_check = datetime.utcnow()
            
            if is_healthy:
                instance.consecutive_failures = 0
            else:
                instance.consecutive_failures += 1
            
            await session.commit()
