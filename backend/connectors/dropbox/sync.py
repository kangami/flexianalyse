"""Dropbox sync job."""
import logging
from uuid import UUID

from connectors.base.models import SyncResult
from connectors.dropbox.service import DropboxService
from models.resource import Resource

logger = logging.getLogger(__name__)


class DropboxSync:
    """Synchronize Dropbox files into local Resource rows."""

    def __init__(self, locator) -> None:
        self._loc = locator
        self._service = DropboxService(locator)

    def run(self, connector_id: str) -> SyncResult:
        result = SyncResult(connector_id=connector_id)
        try:
            client, connector = self._service._build_client(connector_id)
            connector_uuid = UUID(connector_id)
            remote_resources = client.list_resources()

            logger.info(
                "Dropbox sync: %d remote resources found [connector=%s]",
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
                    self._loc.resources.create(
                        Resource(
                            organization_id=connector.organization_id,
                            connector_id=connector_uuid,
                            external_id=remote.uri,
                            type="dropbox_file",
                            title=remote.name,
                            ressource_metadata=meta,
                        )
                    )
                    result.synced_count += 1

            result.finish("success")
        except Exception as exc:
            logger.error("Dropbox sync failed [%s]: %s", connector_id, exc, exc_info=True)
            result.errors.append(str(exc))
            result.finish("failed" if not result.synced_count else "partial")

        return result
