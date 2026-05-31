"""SharePoint sync — upserts remote documents into the local database.

On every run the sync job:
  1. Lists all resources exposed by the SharePoint MCP server.
  2. Creates new Resource rows for documents not yet stored locally.
  3. Updates existing Resource rows whose title or metadata changed.
  4. Returns a SyncResult summary.
"""
import logging
from uuid import UUID

from models.resource import Resource
from connectors.base.models import SyncResult
from connectors.sharepoint.service import SharePointService

logger = logging.getLogger(__name__)


class SharePointSync:
    """Synchronisation job for the SharePoint connector."""

    def __init__(self, locator) -> None:
        self._loc = locator
        self._service = SharePointService(locator)

    def run(self, connector_id: str) -> SyncResult:
        """Execute a full sync for the given connector and return the result."""
        result = SyncResult(connector_id=connector_id)
        try:
            client, connector = self._service._build_client(connector_id)
            connector_uuid = UUID(connector_id)

            remote_resources = client.list_resources()
            logger.info(
                "SharePoint sync: %d remote resources found [connector=%s]",
                len(remote_resources),
                connector_id,
            )

            for remote in remote_resources:
                meta = {
                    "mime_type": remote.mime_type,
                    "description": remote.description,
                    **remote.metadata,
                }
                existing = self._loc.resources.get_by_external_id(connector_uuid, remote.uri)

                if existing:
                    existing.title = remote.name
                    existing.ressource_metadata = meta
                    self._loc.resources.update(existing)
                    result.updated_count += 1
                else:
                    resource = Resource(
                        organization_id=connector.organization_id,
                        connector_id=connector_uuid,
                        external_id=remote.uri,
                        type="sharepoint_document",
                        title=remote.name,
                        ressource_metadata=meta,
                    )
                    self._loc.resources.create(resource)
                    result.synced_count += 1

            result.finish("success")
            logger.info(
                "SharePoint sync complete [connector=%s]: created=%d updated=%d",
                connector_id,
                result.synced_count,
                result.updated_count,
            )

        except Exception as exc:
            logger.error(
                "SharePoint sync failed [connector=%s]: %s",
                connector_id,
                exc,
                exc_info=True,
            )
            result.errors.append(str(exc))
            result.finish("failed" if not result.synced_count else "partial")

        return result
