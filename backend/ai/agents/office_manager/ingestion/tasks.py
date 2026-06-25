"""
Celery tasks for document ingestion — Office Manager agent.

Task hierarchy:
  trigger_ingestion_for_connector   ← entry point
      └── ingest_batch              ← processes 50 files at a time
              └── ingest_single_file ← processes one file
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from celery_app import celery_app
from config.extensions import db
from models.connector import Connector, ConnectorCredentials, ConnectorSync
from models.resource import Resource, ResourceChunk
from services.encryption_service import EncryptionService
from services.mcp_http_client import get_mcp_client
from ai.ingestion.extractor import DocumentExtractor
from ai.ingestion.embedder import Embedder

logger = logging.getLogger(__name__)

BATCH_SIZE = 50

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


def _get_extractor() -> DocumentExtractor:
    global _extractor
    if _extractor is None:
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

    # Embed all chunks in one batch call
    texts = [c.content for c in extraction_result.chunks]
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

    sync = ConnectorSync(
        connector_id=UUID(connector_id),
        status='running',
    )
    db.session.add(sync)
    db.session.commit()
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

        # Create batches of BATCH_SIZE
        batches = [
            files[i:i + BATCH_SIZE]
            for i in range(0, len(files), BATCH_SIZE)
        ]

        if not batches:
            sync.status = 'completed'
            sync.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return {'status': 'completed', 'total_files': 0, 'total_batches': 0}

        sync.total_batches = len(batches)
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

    # Update ConnectorSync atomically
    if sync_id:
        _update_connector_sync(
            sync_id=sync_id,
            processed=len(batch),
            created=results.get('done', 0),
            failed=results.get('failed', 0),
            total_batches=total_batches,
            org_id=org_id,  
        )
    
    # Trigger knowledge graph build if this was the last batch
    if sync_id:
        _update_connector_sync(
            sync_id=sync_id,
            processed=len(batch),
            created=results.get('done', 0),
            failed=results.get('failed', 0),
            total_batches=total_batches,
            org_id=org_id,
        )
        logger.info(f"KG build triggered for org {org_id}")


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
    external_id = file_metadata.get('id') or file_metadata.get('path_lower', '')
    title = file_metadata.get('name', 'Untitled')

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

    # Skip if unchanged
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

        # Extract + chunk
        extraction = _get_extractor().extract(raw_content, mime_type, title)

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
        sync.status = 'failed' if (sync.resources_processed - sync.resources_created) > 0 and sync.resources_created == 0 else 'completed'
        sync.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info(
            f"Sync {sync_id} finished — status={sync.status} "
            f"processed={sync.resources_processed} created={sync.resources_created}"
        )
        if org_id and sync.status == 'completed' and not sync.kg_built:
            sync.kg_built = True
            db.session.commit()
            build_knowledge_graph.delay(org_id=org_id)
            logger.info(f"KG build triggered for org {org_id} after sync {sync_id}")


# ============================================================================
# FILE LISTING HELPERS
# ============================================================================

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
        result = asyncio.run(
            client.list_documents(max_results=1000, access_token=creds.encrypted_token)
        )
        return result.get('documents', [])
    except Exception as e:
        logger.error("Failed to list Google Drive files for connector %s: %s", connector.id, e)
        return []


def _list_dropbox_resources(connector: Connector, org_id: str) -> list[dict]:
    """List all Dropbox files for batching."""
    import asyncio
    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id, deleted_at=None
    ).first()
    if not creds:
        return []

    try:
        access_token = _get_encryption_service().decrypt(creds.encrypted_token)
        client = get_mcp_client('dropbox')
        result = asyncio.run(
            client.list_dropbox_files(
                path="", recursive=True, limit=1000, bearer_token=access_token
            )
        )
        return [e for e in result.get('entries', []) if e.get('tag') == 'file']
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
        logger.error("Failed to list SQL tables for connector %s: %s", connector.id, e)
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

    result = asyncio.run(
        client.download_drive_file_base64(file_id=file_id, mime_type=mime_type)
    )

    content_b64 = result.get('content_base64', '')
    raw_bytes = base64.b64decode(content_b64) if content_b64 else b''
    effective_mime = result.get('mime_type', mime_type)
    return raw_bytes, effective_mime


def _download_dropbox_file(file_metadata: dict, creds) -> tuple[bytes, str]:
    """Download a Dropbox file as raw bytes (binary-safe)."""
    import asyncio
    import base64
    access_token = _get_encryption_service().decrypt(creds.encrypted_token)
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
            f"SELECT * FROM {table_name} LIMIT 100",
            database_url=database_url
        )
    )

    content = f"# Table: {table_name}\n\n"
    content += f"## Schema\n{json.dumps(schema, indent=2)}\n\n"
    content += f"## Sample rows (100)\n{json.dumps(sample, indent=2)}"

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
