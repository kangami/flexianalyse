from typing import Optional, List
from uuid import UUID
from models.resource import Resource, ResourceBinding
from .base import BaseRepository


class ResourceRepository(BaseRepository[Resource]):
    """Accès aux données de la table resources."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Resource]:
        row = self.db.fetch_one(
            "SELECT * FROM resources WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Resource(**row) if row else None

    def get_by_external_id(self, connector_id: UUID, external_id: str) -> Optional[Resource]:
        row = self.db.fetch_one(
            "SELECT * FROM resources WHERE connector_id = %s AND external_id = %s AND deleted_at IS NULL",
            (connector_id, external_id)
        )
        return Resource(**row) if row else None

    def list_by_organization(self, organization_id: UUID, limit: int = 100, offset: int = 0) -> List[Resource]:
        rows = self.db.fetch_all(
            "SELECT * FROM resources WHERE organization_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (organization_id, limit, offset)
        )
        return [Resource(**r) for r in rows]

    def list_by_connector(self, connector_id: UUID) -> List[Resource]:
        rows = self.db.fetch_all(
            "SELECT * FROM resources WHERE connector_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC",
            (connector_id,)
        )
        return [Resource(**r) for r in rows]

    def search_fulltext(self, organization_id: UUID, query: str, limit: int = 50) -> List[Resource]:
        rows = self.db.fetch_all(
            """SELECT * FROM resources
               WHERE organization_id = %s AND deleted_at IS NULL
               AND search_vector @@ plainto_tsquery('french', %s)
               ORDER BY ts_rank(search_vector, plainto_tsquery('french', %s)) DESC
               LIMIT %s""",
            (organization_id, query, query, limit)
        )
        return [Resource(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Resource]:
        rows = self.db.fetch_all(
            "SELECT * FROM resources WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Resource(**r) for r in rows]

    def create(self, entity: Resource) -> Resource:
        row = self.db.fetch_one(
            """INSERT INTO resources (organization_id, connector_id, external_id, type, title, metadata)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.connector_id, entity.external_id,
             entity.type, entity.title, entity.metadata)
        )
        return Resource(**row)

    def update(self, entity: Resource) -> Resource:
        row = self.db.fetch_one(
            """UPDATE resources SET title = %s, metadata = %s, updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.title, entity.metadata, entity.id)
        )
        return Resource(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE resources SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM resources WHERE id = %s", (id,))
        return result.rowcount > 0


class ResourceBindingRepository(BaseRepository[ResourceBinding]):
    """Accès aux données de la table resource_bindings."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[ResourceBinding]:
        row = self.db.fetch_one(
            "SELECT * FROM resource_bindings WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return ResourceBinding(**row) if row else None

    def list_by_resource(self, resource_id: UUID) -> List[ResourceBinding]:
        rows = self.db.fetch_all(
            "SELECT * FROM resource_bindings WHERE resource_id = %s AND deleted_at IS NULL",
            (resource_id,)
        )
        return [ResourceBinding(**r) for r in rows]

    def list_by_tool_scope(self, tool_scope_id: UUID) -> List[ResourceBinding]:
        rows = self.db.fetch_all(
            "SELECT * FROM resource_bindings WHERE tool_scope_id = %s AND deleted_at IS NULL",
            (tool_scope_id,)
        )
        return [ResourceBinding(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ResourceBinding]:
        rows = self.db.fetch_all(
            "SELECT * FROM resource_bindings WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [ResourceBinding(**r) for r in rows]

    def create(self, entity: ResourceBinding) -> ResourceBinding:
        row = self.db.fetch_one(
            """INSERT INTO resource_bindings (resource_id, tool_scope_id, access_level)
               VALUES (%s, %s, %s) RETURNING *""",
            (entity.resource_id, entity.tool_scope_id, entity.access_level)
        )
        return ResourceBinding(**row)

    def update(self, entity: ResourceBinding) -> ResourceBinding:
        row = self.db.fetch_one(
            """UPDATE resource_bindings SET access_level = %s
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.access_level, entity.id)
        )
        return ResourceBinding(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE resource_bindings SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM resource_bindings WHERE id = %s", (id,))
        return result.rowcount > 0
