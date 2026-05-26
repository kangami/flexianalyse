from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, text
from config.extensions import db
from models.resource import Resource, ResourceBinding
from .base import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    """Accès aux données de la table resources."""

    def get_by_id(self, id: UUID) -> Optional[Resource]:
        return db.session.scalars(
            select(Resource).where(Resource.id == id, Resource.deleted_at.is_(None))
        ).first()

    def get_by_external_id(self, connector_id: UUID, external_id: str) -> Optional[Resource]:
        return db.session.scalars(
            select(Resource)
            .where(
                Resource.connector_id == connector_id,
                Resource.external_id == external_id,
                Resource.deleted_at.is_(None),
            )
        ).first()

    def list_by_organization(self, organization_id: UUID, limit: int = 100, offset: int = 0) -> List[Resource]:
        return list(db.session.scalars(
            select(Resource)
            .where(Resource.organization_id == organization_id, Resource.deleted_at.is_(None))
            .order_by(Resource.updated_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def list_by_connector(self, connector_id: UUID) -> List[Resource]:
        return list(db.session.scalars(
            select(Resource)
            .where(Resource.connector_id == connector_id, Resource.deleted_at.is_(None))
            .order_by(Resource.updated_at.desc())
        ).all())

    def search_fulltext(self, organization_id: UUID, query: str, limit: int = 50) -> List[Resource]:
        stmt = text(
            """SELECT * FROM resources
               WHERE organization_id = :org_id AND deleted_at IS NULL
               AND search_vector @@ plainto_tsquery('french', :query)
               ORDER BY ts_rank(search_vector, plainto_tsquery('french', :query)) DESC
               LIMIT :limit"""
        )
        rows = db.session.execute(stmt, {"org_id": organization_id, "query": query, "limit": limit}).mappings().all()
        return [Resource(**dict(r)) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Resource]:
        return list(db.session.scalars(
            select(Resource).where(Resource.deleted_at.is_(None))
            .order_by(Resource.updated_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Resource) -> Resource:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Resource) -> Resource:
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Resource).where(Resource.id == id, Resource.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Resource, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class ResourceBindingRepository(BaseRepository[ResourceBinding]):
    """Accès aux données de la table resource_bindings."""

    def get_by_id(self, id: UUID) -> Optional[ResourceBinding]:
        return db.session.scalars(
            select(ResourceBinding)
            .where(ResourceBinding.id == id, ResourceBinding.deleted_at.is_(None))
        ).first()

    def list_by_resource(self, resource_id: UUID) -> List[ResourceBinding]:
        return list(db.session.scalars(
            select(ResourceBinding)
            .where(ResourceBinding.resource_id == resource_id, ResourceBinding.deleted_at.is_(None))
        ).all())

    def list_by_tool_scope(self, tool_scope_id: UUID) -> List[ResourceBinding]:
        return list(db.session.scalars(
            select(ResourceBinding)
            .where(ResourceBinding.tool_scope_id == tool_scope_id, ResourceBinding.deleted_at.is_(None))
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ResourceBinding]:
        return list(db.session.scalars(
            select(ResourceBinding).where(ResourceBinding.deleted_at.is_(None))
            .order_by(ResourceBinding.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: ResourceBinding) -> ResourceBinding:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: ResourceBinding) -> ResourceBinding:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(ResourceBinding).where(ResourceBinding.id == id, ResourceBinding.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(ResourceBinding, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
