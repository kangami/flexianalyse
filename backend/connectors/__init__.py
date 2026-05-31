"""MCP Connectors package.

Supported connector types:
  - google_drive  → GoogleDriveService / GoogleDriveSync
  - sharepoint    → SharePointService  / SharePointSync
  - sql           → SQLService         / SQLSync
"""
from connectors.google_drive.service import GoogleDriveService
from connectors.google_drive.sync import GoogleDriveSync
from connectors.sharepoint.service import SharePointService
from connectors.sharepoint.sync import SharePointSync
from connectors.sql.service import SQLService
from connectors.sql.sync import SQLSync

CONNECTOR_TYPES: list[str] = ["google_drive", "sharepoint", "sql"]

_SERVICE_MAP: dict = {
    "google_drive": (GoogleDriveService, GoogleDriveSync),
    "sharepoint":   (SharePointService,  SharePointSync),
    "sql":          (SQLService,          SQLSync),
}


def get_service(connector_type: str, locator):
    """Return an instantiated service for the given connector type."""
    entry = _SERVICE_MAP.get(connector_type)
    if not entry:
        raise ValueError(f"Unknown connector type '{connector_type}'. Valid: {CONNECTOR_TYPES}")
    svc_cls, _ = entry
    return svc_cls(locator)


def get_sync(connector_type: str, locator):
    """Return an instantiated sync job for the given connector type."""
    entry = _SERVICE_MAP.get(connector_type)
    if not entry:
        raise ValueError(f"Unknown connector type '{connector_type}'. Valid: {CONNECTOR_TYPES}")
    _, sync_cls = entry
    return sync_cls(locator)


__all__ = [
    "CONNECTOR_TYPES",
    "get_service",
    "get_sync",
    "GoogleDriveService",
    "GoogleDriveSync",
    "SharePointService",
    "SharePointSync",
    "SQLService",
    "SQLSync",
]
