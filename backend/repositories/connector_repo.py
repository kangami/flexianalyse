from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.connector import Connector, ConnectorCredentials, ToolScope
from .base import BaseRepository


class ConnectorRepository(BaseRepository[Connector]):
    """Accès aux données de la table connectors."""

    def get_by_id(self, id: UUID) -> Optional[Connector]:
        return db.session.scalars(
            select(Connector).where(Connector.id == id, Connector.deleted_at.is_(None))
        ).first()

    def list_by_organization(self, organization_id: UUID) -> List[Connector]:
        return list(db.session.scalars(
            select(Connector)
            .where(Connector.organization_id == organization_id, Connector.deleted_at.is_(None))
            .order_by(Connector.created_at.desc())
        ).all())

    def list_active_by_organization(self, organization_id: UUID) -> List[Connector]:
        return list(db.session.scalars(
            select(Connector)
            .where(
                Connector.organization_id == organization_id,
                Connector.status == 'active',
                Connector.deleted_at.is_(None),
            )
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Connector]:
        return list(db.session.scalars(
            select(Connector).where(Connector.deleted_at.is_(None))
            .order_by(Connector.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Connector) -> Connector:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Connector) -> Connector:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Connector).where(Connector.id == id, Connector.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.now(timezone.utc)
        # Also flip status so any query keyed on status (not just deleted_at)
        # excludes it too — defensive, keeps the two flags consistent.
        entity.status = 'inactive'
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Connector, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class ConnectorCredentialsRepository(BaseRepository[ConnectorCredentials]):
    """Accès aux données de la table connector_credentials."""

    def get_by_id(self, id: UUID) -> Optional[ConnectorCredentials]:
        return db.session.scalars(
            select(ConnectorCredentials)
            .where(ConnectorCredentials.id == id, ConnectorCredentials.deleted_at.is_(None))
        ).first()

    def get_by_connector(self, connector_id: UUID) -> Optional[ConnectorCredentials]:
        return db.session.scalars(
            select(ConnectorCredentials)
            .where(ConnectorCredentials.connector_id == connector_id, ConnectorCredentials.deleted_at.is_(None))
        ).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ConnectorCredentials]:
        return list(db.session.scalars(
            select(ConnectorCredentials).where(ConnectorCredentials.deleted_at.is_(None))
            .order_by(ConnectorCredentials.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: ConnectorCredentials) -> ConnectorCredentials:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: ConnectorCredentials) -> ConnectorCredentials:
        entity.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(ConnectorCredentials)
            .where(ConnectorCredentials.id == id, ConnectorCredentials.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(ConnectorCredentials, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class ToolScopeRepository(BaseRepository[ToolScope]):
    """Accès aux données de la table tool_scopes."""

    def get_by_id(self, id: UUID) -> Optional[ToolScope]:
        return db.session.scalars(
            select(ToolScope).where(ToolScope.id == id, ToolScope.deleted_at.is_(None))
        ).first()

    def list_by_connector(self, connector_id: UUID) -> List[ToolScope]:
        return list(db.session.scalars(
            select(ToolScope)
            .where(ToolScope.connector_id == connector_id, ToolScope.deleted_at.is_(None))
            .order_by(ToolScope.scope_type, ToolScope.name)
        ).all())

    def list_allowed_by_connector(self, connector_id: UUID) -> List[ToolScope]:
        return list(db.session.scalars(
            select(ToolScope)
            .where(
                ToolScope.connector_id == connector_id,
                ToolScope.is_allowed.is_(True),
                ToolScope.deleted_at.is_(None),
            )
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolScope]:
        return list(db.session.scalars(
            select(ToolScope).where(ToolScope.deleted_at.is_(None))
            .order_by(ToolScope.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: ToolScope) -> ToolScope:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: ToolScope) -> ToolScope:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(ToolScope).where(ToolScope.id == id, ToolScope.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(ToolScope, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
