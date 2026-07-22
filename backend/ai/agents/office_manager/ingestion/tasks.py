"""
Celery tasks for document ingestion — Office Manager agent.

Task hierarchy:
  trigger_ingestion_for_connector   ← entry point
      └── ingest_batch              ← processes 50 files at a time
              └── ingest_single_file ← processes one file
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import requests

from sqlalchemy import or_

from celery_app import celery_app
from config.extensions import db
from models.connector import Connector, ConnectorCredentials, ConnectorSync
from models.resource import Resource, ResourceChunk
from models.knowledge_graph import KGNode, KGEdge
from services.encryption_service import EncryptionService
from services.mcp_http_client import get_mcp_client
# NOTE: `ai.ingestion.extractor` (docling → torch/transformers/onnx) is imported
# LAZILY inside _get_extractor(), not here. The API process imports this module
# only to ENQUEUE ingestion tasks; keeping the heavy import out of module scope
# lets the API run without docling/onnx installed (worker-only deps).
from ai.ingestion.embedder import Embedder
from ai.ingestion.router import classify_document

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
SQL_SAMPLE_ROWS = 20  # rows captured per table for semantic search (live data via Text-to-SQL)

# Skip downloading files larger than this — avoids long downloads / ReadTimeouts
# on huge binaries that we can't process anyway (ISO, video, archives...).
MAX_DOWNLOAD_BYTES = int(os.getenv('MAX_INGEST_FILE_MB', '50')) * 1024 * 1024


def _coerce_int(value) -> int:
    """Best-effort int parse (file sizes arrive as str from some connectors)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

# Lazy singletons — initialized on first use inside a worker process,
# NOT at import time (avoids model loading during Celery autodiscovery).
_encryption_service = None
_extractor = None
_embedder = None


def _get_encryption_service() -> EncryptionService:
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def _get_extractor():
    global _extractor
    if _extractor is None:
        # Lazy heavy import (docling → torch/transformers/onnx) — worker only.
        from ai.ingestion.extractor import DocumentExtractor
        _extractor = DocumentExtractor()
    return _extractor


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder

# ============================================================================
# HELPERS
# ============================================================================

def _resource_external_id(file_metadata: dict) -> str:
    """Canonical external id for a remote item — same key used everywhere
    (ingestion upsert AND deletion reconciliation must agree)."""
    return file_metadata.get('id') or file_metadata.get('path_lower', '')


def _reconcile_deletions(connector_id: str, org_id: str, remote_files: list[dict]) -> int:
    """Soft-delete local resources that no longer exist at the source.

    Compares the freshly listed remote ids against stored resources and removes
    the stragglers (resource + its chunks + its KG node/edges).

    Safety: if the remote listing is empty we skip entirely — an empty list is
    indistinguishable from a listing failure, and mass-deleting on a transient
    error would be catastrophic.
    """
    remote_ids = {
        _resource_external_id(f) for f in remote_files
        if _resource_external_id(f)
    }
    if not remote_ids:
        logger.info("Reconciliation skipped (empty remote listing) for connector %s", connector_id)
        return 0

    stale = Resource.query.filter(
        Resource.connector_id == UUID(connector_id),
        Resource.organization_id == UUID(org_id),
        Resource.deleted_at.is_(None),
        Resource.external_id.isnot(None),
        Resource.external_id.notin_(remote_ids),
    ).all()

    deleted = 0
    now = datetime.now(timezone.utc)
    for resource in stale:
        ResourceChunk.query.filter_by(resource_id=resource.id).delete()

        node = KGNode.query.filter_by(
            org_id=org_id, external_id=f"resource:{resource.id}"
        ).first()
        if node:
            KGEdge.query.filter(
                or_(KGEdge.source_id == node.id, KGEdge.target_id == node.id)
            ).delete(synchronize_session=False)
            db.session.delete(node)

        resource.deleted_at = now
        resource.ingestion_status = 'deleted'
        deleted += 1

    db.session.commit()
    if deleted:
        logger.info("Reconciliation: soft-deleted %d stale resources for connector %s", deleted, connector_id)
    return deleted


def _should_skip(resource: Resource, file_metadata: dict) -> bool:
    """Returns True if file hasn't changed since last sync."""
    if resource.ingestion_status not in ('done', 'skipped'):
        return False

    # 1 — Version ID
    new_version = (
        file_metadata.get('version') or
        file_metadata.get('rev') or
        file_metadata.get('headRevisionId')
    )
    if new_version and resource.external_version:
        return new_version == resource.external_version

    # 2 — Modified date
    from dateutil import parser as dateparser
    raw_date = (
        file_metadata.get('modifiedTime') or
        file_metadata.get('server_modified') or
        file_metadata.get('modified')
    )
    if raw_date and resource.external_modified_at:
        new_dt = dateparser.parse(raw_date) if isinstance(raw_date, str) else raw_date
        if new_dt and new_dt <= resource.external_modified_at:
            return True

    return False


def _update_resource_version(resource: Resource, raw_content: bytes, file_metadata: dict):
    """Update versioning fields after successful ingestion."""
    import hashlib
    from dateutil import parser as dateparser

    resource.content_hash = hashlib.sha256(raw_content).hexdigest()
    resource.ingestion_status = 'done'
    resource.ingested_at = datetime.now(timezone.utc)
    resource.file_size_bytes = len(raw_content)
    resource.external_version = (
        file_metadata.get('version') or
        file_metadata.get('rev') or
        file_metadata.get('headRevisionId')
    )
    raw_date = (
        file_metadata.get('modifiedTime') or
        file_metadata.get('server_modified') or
        file_metadata.get('modified')
    )
    if raw_date:
        resource.external_modified_at = (
            dateparser.parse(raw_date)
            if isinstance(raw_date, str) else raw_date
        )


def _save_chunks(resource: Resource, extraction_result):
    """Delete old chunks and save new ones with embeddings."""

    # Delete existing chunks
    ResourceChunk.query.filter_by(resource_id=resource.id).delete()

    if not extraction_result.chunks:
        return

    # Embed each chunk WITH its document title + section as context (contextual
    # retrieval): an ambiguous chunk like "Net à payer : 1373,22" becomes
    # "Bulletin-Paie-Bernis › Salaire\nNet à payer : 1373,22", which the dense
    # retriever can match to a person/topic query. The raw content is stored
    # unchanged; only the embedded text is enriched.
    doc_title = resource.title or ''

    def _embed_text(c) -> str:
        prefix = ' › '.join(p for p in (doc_title, c.section_title or '') if p)
        return f"{prefix}\n{c.content}" if prefix else c.content

    texts = [_embed_text(c) for c in extraction_result.chunks]
    embeddings = _get_embedder().embed_chunks(texts)

    for chunk, embedding in zip(extraction_result.chunks, embeddings):
        db_chunk = ResourceChunk(
            resource_id=resource.id,
            organization_id=resource.organization_id,
            connector_id=resource.connector_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            chunk_type=chunk.chunk_type,
            embedding=embedding,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            token_count=chunk.token_count,
            chunk_metadata=chunk.chunk_metadata,
        )
        db.session.add(db_chunk)


# ============================================================================
# TASK 1 — ENTRY POINT : lists files and creates batches
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def trigger_ingestion_for_connector(self, connector_id: str, org_id: str):
    """
    Entry point — lists all files for a connector and dispatches batches.
    Called automatically when a connector is created, or manually via API.
    """
    logger.info(f"Starting ingestion for connector {connector_id}")

    # One sync row per connector, reused on every sync (set to 'running' now,
    # flipped to 'completed'/'failed' when it ends).
    sync = _reset_sync_for_connector(connector_id)
    sync_id = str(sync.id)

    try:
        connector = Connector.query.get(UUID(connector_id))
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")

        if connector.type == 'sql':
            files = _list_sql_resources(connector, org_id)
        elif connector.type == 'google_drive':
            files = _list_drive_resources(connector, org_id)
        elif connector.type == 'dropbox':
            files = _list_dropbox_resources(connector, org_id)
        else:
            logger.warning(f"Unsupported connector type: {connector.type}")
            sync.status = 'completed'
            sync.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return {'status': 'skipped', 'reason': 'unsupported connector type'}

        # Reconcile deletions — drop local resources gone from the source.
        # Limited to file connectors: SQL tables are rarely dropped and the SQL
        # path uses a different external_id scheme (table name vs URI), so
        # reconciling them could wrongly delete SQLSync-created resources.
        deleted_count = 0
        if connector.type in ('google_drive', 'dropbox'):
            deleted_count = _reconcile_deletions(connector_id, org_id, files)

        # Create batches of BATCH_SIZE
        batches = [
            files[i:i + BATCH_SIZE]
            for i in range(0, len(files), BATCH_SIZE)
        ]

        if not batches:
            sync.status = 'completed'
            sync.completed_at = datetime.now(timezone.utc)
            sync.resources_deleted = deleted_count
            db.session.commit()
            return {
                'status': 'completed',
                'total_files': 0,
                'total_batches': 0,
                'deleted': deleted_count,
            }

        sync.total_batches = len(batches)
        sync.resources_deleted = deleted_count
        db.session.commit()

        logger.info(
            f"Connector {connector_id}: {len(files)} files → "
            f"{len(batches)} batches of {BATCH_SIZE}"
        )

        # Dispatch each batch as a separate Celery task
        for batch_idx, batch in enumerate(batches):
            ingest_batch.delay(
                batch=batch,
                connector_id=connector_id,
                connector_type=connector.type,
                org_id=org_id,
                batch_idx=batch_idx,
                total_batches=len(batches),
                sync_id=sync_id,
            )

        return {
            'status': 'dispatched',
            'sync_id': sync_id,
            'total_files': len(files),
            'total_batches': len(batches),
            'deleted': deleted_count,
        }

    except Exception as e:
        logger.error(f"trigger_ingestion failed: {e}", exc_info=True)
        sync.status = 'failed'
        sync.completed_at = datetime.now(timezone.utc)
        sync.error_message = str(e)
        db.session.commit()
        raise self.retry(exc=e, countdown=60)


# ============================================================================
# TASK 2 — BATCH PROCESSOR
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def ingest_batch(
    self,
    batch: list[dict],
    connector_id: str,
    connector_type: str,
    org_id: str,
    batch_idx: int,
    total_batches: int,
    sync_id: str = None,
):
    """Process a batch of files."""
    logger.info(
        f"Processing batch {batch_idx + 1}/{total_batches} "
        f"({len(batch)} files) for connector {connector_id}"
    )

    results = {'done': 0, 'skipped': 0, 'failed': 0}

    for file_metadata in batch:
        try:
            result = ingest_single_file(
                file_metadata=file_metadata,
                connector_id=connector_id,
                connector_type=connector_type,
                org_id=org_id,
            )
            results[result] = results.get(result, 0) + 1
        except Exception as e:
            logger.error(
                f"Failed to ingest file {file_metadata.get('id', '?')}: {e}",
                exc_info=True
            )
            results['failed'] += 1

    logger.info(f"Batch {batch_idx + 1} complete: {results}")

    # Update ConnectorSync atomically. The last batch to report in marks the
    # sync complete and triggers the KG build (both handled inside the helper).
    if sync_id:
        _update_connector_sync(
            sync_id=sync_id,
            processed=len(batch),
            created=results.get('done', 0),
            failed=results.get('failed', 0),
            total_batches=total_batches,
            org_id=org_id,
        )

    return results


# ============================================================================
# TASK 3 — SINGLE FILE PROCESSOR
# ============================================================================

def ingest_single_file(
    file_metadata: dict,
    connector_id: str,
    connector_type: str,
    org_id: str,
) -> str:
    """
    Ingest a single file — download, extract, embed, save.
    Returns 'done', 'skipped', or 'failed'.
    """
    external_id = _resource_external_id(file_metadata)
    title = file_metadata.get('name', 'Untitled')

    # Pre-filter BEFORE any DB write — unsupported types (ISO/APK/MP4/SVG...) and
    # oversized files are NEVER persisted as resources (no junk 'skipped' rows,
    # and no wasted download / ReadTimeout). File connectors only.
    if connector_type != 'sql':
        # Drive puts the MIME in 'type'; Dropbox has none → fall back to the
        # filename extension inside is_supported().
        mime = (file_metadata.get('type') or file_metadata.get('mimeType')
                or file_metadata.get('mime_type') or '')
        if not _get_extractor().is_supported(mime, title):
            logger.info(f"Skipped (unsupported type, not saved): {title}")
            return 'skipped'

        size = _coerce_int(file_metadata.get('size') or file_metadata.get('bytes'))
        if size and size > MAX_DOWNLOAD_BYTES:
            logger.info(f"Skipped (too large, not saved, {size} bytes): {title}")
            return 'skipped'

    # Upsert Resource record
    resource = Resource.query.filter_by(
        organization_id=org_id,
        connector_id=connector_id,
        external_id=external_id,
        deleted_at=None
    ).first()

    if not resource:
        resource = Resource(
            organization_id=UUID(org_id),
            connector_id=UUID(connector_id),
            external_id=external_id,
            title=title,
            type=connector_type,
            ingestion_status='pending',
            ressource_metadata=file_metadata,
        )
        db.session.add(resource)
        db.session.flush()

    # Skip if unchanged — the resource already exists and is valid, so we keep
    # it (only NEW unsupported/oversized files are filtered, above, with no row).
    if _should_skip(resource, file_metadata):
        resource.ingestion_status = 'skipped'
        db.session.commit()
        logger.info(f"Skipped (unchanged): {title}")
        return 'skipped'

    # Mark as processing
    resource.ingestion_status = 'processing'
    resource.title = title
    resource.ressource_metadata = file_metadata
    db.session.commit()

    try:
        # Download content
        raw_content, mime_type = _download_file(
            file_metadata, connector_id, connector_type, org_id
        )

        if not raw_content:
            resource.ingestion_status = 'failed'
            resource.ingestion_error = 'Empty content'
            db.session.commit()
            return 'failed'

        # Adaptive ingestion router — classify the document and pick a strategy.
        extractor = _get_extractor()
        file_format = extractor.detect_format(mime_type, title)
        sample = extractor.sample_text(raw_content, file_format, title) if file_format else ""
        route = classify_document(file_format or '', title, sample)
        # Record the routing decision on the resource (visibility + future filtering).
        resource.ressource_metadata = {
            **(file_metadata or {}),
            "doc_type": route.doc_type,
            "ingestion_strategy": route.strategy,
            "route_confidence": route.confidence,
        }

        # Extract + chunk (strategy-aware; generic path until per-strategy is wired)
        extraction = extractor.extract(raw_content, mime_type, title, strategy=route.strategy)

        if not extraction.success:
            if extraction.file_format == 'unsupported':
                resource.ingestion_status = 'skipped'
                resource.ingestion_error = extraction.error
                db.session.commit()
                logger.info(f"Skipped (unsupported): {title}")
                return 'skipped'
                
            resource.ingestion_status = 'failed'
            resource.ingestion_error = extraction.error
            db.session.commit()
            logger.warning(f"Extraction failed for {title}: {extraction.error}")
            return 'failed'

        # Save chunks with embeddings
        _save_chunks(resource, extraction)

        # Update versioning
        _update_resource_version(resource, raw_content, file_metadata)
        db.session.commit()

        logger.info(
            f"Ingested: {title} → {len(extraction.chunks)} chunks "
            f"({extraction.raw_size_bytes} bytes)"
        )
        return 'done'

    except Exception as e:
        resource.ingestion_status = 'failed'
        resource.ingestion_error = str(e)
        db.session.commit()
        logger.error(f"Ingestion error for {title}: {e}", exc_info=True)
        return 'failed'


# ============================================================================
# SYNC TRACKING HELPER
# ============================================================================

def _reset_sync_for_connector(connector_id: str) -> ConnectorSync:
    """Return the single ConnectorSync row for a connector (creating it if
    missing), reset for a fresh run. Any duplicate/legacy rows are removed so
    there is exactly ONE sync record per connector."""
    cid = UUID(connector_id)
    rows = (
        ConnectorSync.query
        .filter_by(connector_id=cid)
        .order_by(ConnectorSync.started_at.desc())
        .all()
    )
    sync = rows[0] if rows else None
    for extra in rows[1:]:        # collapse historical duplicates → one row
        db.session.delete(extra)

    if sync is None:
        sync = ConnectorSync(connector_id=cid)
        db.session.add(sync)

    now = datetime.now(timezone.utc)
    sync.status = 'running'
    sync.started_at = now
    sync.completed_at = None
    sync.error_message = None
    sync.resources_processed = 0
    sync.resources_created = 0
    sync.resources_updated = 0
    sync.resources_deleted = 0
    sync.total_batches = 0
    sync.batches_completed = 0
    sync.kg_built = False
    db.session.commit()
    return sync


def _update_connector_sync(
    sync_id: str,
    processed: int,
    created: int,
    failed: int,
    total_batches: int,
    org_id: str = None
):
    """
    Atomically increment ConnectorSync counters.
    Marks the sync as 'completed' (or 'failed') when the last batch reports in.
    Uses a SQL UPDATE to avoid race conditions between concurrent batch workers.
    """
    from sqlalchemy import text

    db.session.execute(
        text("""
            UPDATE connector_syncs
            SET
                resources_processed  = resources_processed  + :processed,
                resources_created    = resources_created    + :created,
                resources_updated    = resources_updated    + 0,
                resources_deleted    = resources_deleted    + 0,
                batches_completed    = batches_completed    + 1
            WHERE id = :sync_id
        """),
        {'processed': processed, 'created': created, 'sync_id': sync_id},
    )
    db.session.commit()

    # Re-fetch to check if this was the last batch
    sync = ConnectorSync.query.get(UUID(sync_id))
    if sync and sync.batches_completed >= sync.total_batches:
        # The sync completed: per-file failures (or files skipped as unchanged)
        # are tracked on each Resource, NOT on the sync — a re-sync where nothing
        # changed is a success, not a failure. Only listing/dispatch errors
        # (handled in trigger_ingestion's except) mark the sync 'failed'.
        sync.status = 'completed'
        sync.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info(
            f"Sync {sync_id} finished — status={sync.status} "
            f"processed={sync.resources_processed} created={sync.resources_created}"
        )
        if org_id and sync.status == 'completed' and not sync.kg_built:
            # Only (re)build the KG when something actually changed — new/updated
            # resources ingested, or stale ones deleted. A no-change re-sync
            # (everything skipped) must NOT trigger a build.
            has_changes = (sync.resources_created or 0) > 0 or (sync.resources_deleted or 0) > 0
            if has_changes:
                sync.kg_built = True
                db.session.commit()
                build_knowledge_graph.delay(org_id=org_id)
                logger.info(
                    f"KG build triggered for org {org_id} after sync {sync_id} "
                    f"(created={sync.resources_created}, deleted={sync.resources_deleted})"
                )
            else:
                logger.info(
                    f"Sync {sync_id}: no changes (all skipped) — KG build skipped"
                )


# ============================================================================
# FILE LISTING HELPERS
# ============================================================================

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _get_drive_access_token(creds) -> str | None:
    """Return a valid Google Drive access token, refreshing it when expired.

    Google access tokens live ~1h. We keep the raw access token in
    `encrypted_token` and the refresh token in `refresh_token`; when the token is
    (near) expired we exchange the refresh token for a new one and persist it,
    so re-syncs keep working indefinitely.
    """
    if not creds:
        return None

    now = datetime.now(timezone.utc)

    # Still valid (with 60s headroom) → use as-is.
    if creds.encrypted_token and creds.expires_at:
        exp = creds.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp - now > timedelta(seconds=60):
            return creds.encrypted_token

    if not creds.refresh_token:
        logger.warning("Drive token expired and no refresh_token — using stored token as-is")
        return creds.encrypted_token

    try:
        resp = requests.post(
            _GOOGLE_TOKEN_URL,
            data={
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "refresh_token": creds.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))

        creds.encrypted_token = new_token
        creds.expires_at = now + timedelta(seconds=expires_in)
        db.session.commit()
        logger.info("Refreshed Google Drive access token (expires in %ss)", expires_in)
        return new_token
    except Exception as e:
        logger.error("Google Drive token refresh failed: %s", e, exc_info=True)
        return creds.encrypted_token


def _list_drive_resources(connector: Connector, org_id: str) -> list[dict]:
    """List all Drive files for batching."""
    import asyncio
    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id, deleted_at=None
    ).first()
    if not creds:
        return []

    try:
        client = get_mcp_client('google_drive')
        access_token = _get_drive_access_token(creds)
        documents: list[dict] = []
        page_token = None
        while True:
            result = asyncio.run(
                client.list_documents(
                    max_results=1000,
                    access_token=access_token,
                    page_token=page_token,
                )
            )
            documents.extend(result.get('documents', []))
            page_token = result.get('next_page_token')
            if not page_token:
                break
        return documents
    except Exception as e:
        logger.error("Failed to list Google Drive files for connector %s: %s", connector.id, e)
        return []


_DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"


def _get_dropbox_access_token(creds) -> str | None:
    """Return a valid Dropbox access token, refreshing via the stored refresh
    token when expired (Dropbox short-lived tokens last ~4h). Both the access
    token and refresh token are stored ENCRYPTED for Dropbox."""
    if not creds or not creds.encrypted_token:
        return None
    enc = _get_encryption_service()
    now = datetime.now(timezone.utc)

    # Still valid (with 60s headroom)?
    if creds.expires_at:
        exp = creds.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp - now > timedelta(seconds=60):
            try:
                return enc.decrypt(creds.encrypted_token)
            except Exception:
                pass

    if not creds.refresh_token:
        logger.warning("Dropbox token expired and no refresh_token stored")
        try:
            return enc.decrypt(creds.encrypted_token)
        except Exception:
            return None

    try:
        refresh_token = enc.decrypt(creds.refresh_token)
        resp = requests.post(
            _DROPBOX_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(os.getenv("DROPBOX_CLIENT_ID"), os.getenv("DROPBOX_CLIENT_SECRET")),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data["access_token"]
        expires_in = int(data.get("expires_in", 14400))
        creds.encrypted_token = enc.encrypt(new_token)
        creds.expires_at = now + timedelta(seconds=expires_in)
        db.session.commit()
        logger.info("Refreshed Dropbox access token (expires in %ss)", expires_in)
        return new_token
    except Exception as e:
        logger.error("Dropbox token refresh failed: %s", e, exc_info=True)
        try:
            return enc.decrypt(creds.encrypted_token)
        except Exception:
            return None


def _list_dropbox_resources(connector: Connector, org_id: str) -> list[dict]:
    """List all Dropbox files for batching."""
    import asyncio
    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id, deleted_at=None
    ).first()
    if not creds:
        return []

    try:
        access_token = _get_dropbox_access_token(creds)
        client = get_mcp_client('dropbox')

        entries: list[dict] = []
        result = asyncio.run(
            client.list_dropbox_files(
                path="", recursive=True, limit=2000, bearer_token=access_token
            )
        )
        # Surface auth/API errors instead of silently treating them as "0 files".
        if result.get('status') == 'error':
            logger.error(
                "Dropbox listing failed for connector %s: %s",
                connector.id, result.get('message') or result.get('detail') or result,
            )
            return []
        entries.extend(result.get('entries', []))

        # Follow the cursor until Dropbox reports no more pages
        while result.get('has_more') and result.get('cursor'):
            result = asyncio.run(
                client.continue_dropbox_files(
                    cursor=result['cursor'], bearer_token=access_token
                )
            )
            entries.extend(result.get('entries', []))

        return [e for e in entries if e.get('tag') == 'file']
    except Exception as e:
        logger.error("Failed to list Dropbox files for connector %s: %s", connector.id, e)
        return []


def _list_sql_resources(connector: Connector, org_id: str) -> list[dict]:
    """List all SQL tables as 'files' for batching."""
    import asyncio
    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id, deleted_at=None
    ).first()
    if not creds:
        return []

    try:
        database_url = _get_encryption_service().decrypt(creds.encrypted_token)
        client = get_mcp_client('sql')
        result = asyncio.run(
            client.show_tables(database_url=database_url)
        )
        # Represent each table as a "file" with id = table name
        return [
            {'id': table, 'name': table, 'type': 'sql_table'}
            for table in result.get('tables', [])
        ]
    except Exception as e:
        # repr(e) — several driver/timeout exceptions have an empty str(e), which
        # made this log unhelpfully blank; repr keeps the type and any detail.
        logger.error("Failed to list SQL tables for connector %s: %r", connector.id, e)
        return []


# ============================================================================
# DOWNLOAD HELPERS
# ============================================================================

def _download_file(
    file_metadata: dict,
    connector_id: str,
    connector_type: str,
    org_id: str,
) -> tuple[bytes, str]:
    """Download file content and return (raw_bytes, mime_type)."""
    creds = ConnectorCredentials.query.filter_by(
        connector_id=UUID(connector_id), deleted_at=None
    ).first()

    if connector_type == 'google_drive':
        return _download_drive_file(file_metadata, creds)

    elif connector_type == 'dropbox':
        return _download_dropbox_file(file_metadata, creds)

    elif connector_type == 'sql':
        return _download_sql_table(file_metadata, creds)

    return b'', ''


def _download_drive_file(file_metadata: dict, creds) -> tuple[bytes, str]:
    """Download a Google Drive file via the Google Drive MCP server (binary-safe)."""
    import asyncio
    import base64

    file_id = file_metadata.get('id')
    mime_type = file_metadata.get('type', '')
    client = get_mcp_client('google_drive')

    # The MCP server needs the user's OAuth token to act as them (the service
    # account can't see their files); refresh it if expired.
    access_token = _get_drive_access_token(creds)

    result = asyncio.run(
        client.download_drive_file_base64(
            file_id=file_id, mime_type=mime_type, access_token=access_token
        )
    )

    content_b64 = result.get('content_base64', '')
    raw_bytes = base64.b64decode(content_b64) if content_b64 else b''
    effective_mime = result.get('mime_type', mime_type)
    return raw_bytes, effective_mime


def _download_dropbox_file(file_metadata: dict, creds) -> tuple[bytes, str]:
    """Download a Dropbox file as raw bytes (binary-safe)."""
    import asyncio
    import base64
    access_token = _get_dropbox_access_token(creds)
    client = get_mcp_client('dropbox')

    path = file_metadata.get('path_display') or file_metadata.get('path_lower')
    result = asyncio.run(
        client.download_dropbox_file_base64(path, bearer_token=access_token)
    )

    content_b64 = result.get('content_base64', '')
    raw_bytes = base64.b64decode(content_b64) if content_b64 else b''
    mime = _mime_from_filename(file_metadata.get('name', ''))
    return raw_bytes, mime


def _download_sql_table(file_metadata: dict, creds) -> tuple[bytes, str]:
    """Get SQL table schema + sample rows as text."""
    import asyncio
    import json

    database_url = _get_encryption_service().decrypt(creds.encrypted_token)
    client = get_mcp_client('sql')
    table_name = file_metadata.get('id')

    schema = asyncio.run(
        client.describe_table(table_name, database_url=database_url)
    )
    sample = asyncio.run(
        client.query_database(
            f"SELECT * FROM {table_name}",
            limit=SQL_SAMPLE_ROWS,
            database_url=database_url
        )
    )

    content = f"# Table: {table_name}\n\n"
    content += f"## Schema\n{json.dumps(schema, indent=2)}\n\n"
    content += f"## Sample rows ({SQL_SAMPLE_ROWS})\n{json.dumps(sample, indent=2)}"

    return content.encode('utf-8'), 'text/plain'


def _mime_from_filename(filename: str) -> str:
    """Guess MIME type from file extension."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'html': 'text/html',
        'py': 'text/x-python',
        'js': 'text/javascript',
        'json': 'application/json',
    }.get(ext, 'text/plain')

# ============================================================================
# TASK 4 — KNOWLEDGE GRAPH BUILDER
# ============================================================================
def start_ingestion(connector_id: str, org_id: str) -> str | None:
    """Enqueue the ingestion pipeline for a connector.

    Safe to call from web request handlers (connector creation, OAuth callbacks):
    it never raises — a broker hiccup must not fail the HTTP request. Returns the
    Celery task id, or None if enqueuing failed.
    """
    try:
        task = trigger_ingestion_for_connector.delay(str(connector_id), str(org_id))
        logger.info("Ingestion enqueued for connector %s (task %s)", connector_id, task.id)
        return task.id
    except Exception as e:
        logger.error(
            "Failed to enqueue ingestion for connector %s: %s",
            connector_id, e, exc_info=True
        )
        return None


@celery_app.task(bind=True, max_retries=2)
def crawl_connector_schema_task(self, connector_id: str, org_id: str):
    """Crawl + catalogue le schéma d'un connecteur SQL (tâche de fond)."""
    from services.schema_catalog import crawl_connector_schema
    return crawl_connector_schema(connector_id, org_id)


def start_schema_crawl(connector_id: str, org_id: str) -> str | None:
    """Enfile un crawl de schéma. Ne lève jamais (sûr depuis un handler HTTP).

    Marque le connecteur 'pending' tout de suite pour que l'UI le reflète avant
    que le worker ne prenne la tâche. Renvoie l'id de tâche, ou None si l'enfilage
    a échoué (broker indisponible)."""
    try:
        connector = Connector.query.get(UUID(str(connector_id)))
        if connector:
            connector.schema_crawl_status = "pending"
            db.session.commit()
        task = crawl_connector_schema_task.delay(str(connector_id), str(org_id))
        logger.info("Schema crawl enqueued for connector %s (task %s)", connector_id, task.id)
        return task.id
    except Exception as e:
        logger.error("Failed to enqueue schema crawl for %s: %s", connector_id, e, exc_info=True)
        return None


@celery_app.task(bind=True, max_retries=3)
def build_knowledge_graph(self, org_id: str, sync_id: str = None):
    """Build the knowledge graph for an org after ingestion completes."""
    logger.info(f"Building KG for org {org_id}")
    try:
        from ai.knowledge.knowledge_graph_builder import build_kg_for_org
        result = build_kg_for_org(org_id)
        logger.info(f"KG build complete for org {org_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"KG build failed for org {org_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)
