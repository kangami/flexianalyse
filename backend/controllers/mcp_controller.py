"""
MCP Controller — Flask routes for MCP server interactions.
Connects Flask to shared MCP Docker servers via HTTP.
Supports multi-org connector management.
"""

import logging
from flask import request, jsonify, Blueprint
from services.mcp_http_client import get_mcp_client, MCP_SERVERS, MCPHttpClient
from models.connector import Connector, ConnectorCredentials
from config.extensions import db
from services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)
encryption_service = EncryptionService()

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')


# ============================================================================
# HELPERS
# ============================================================================

def _get_org_id() -> str | None:
    """Récupère l'org_id depuis le header."""
    return request.headers.get('X-Organization-Id')


def _get_database_url_for_org(org_id: str) -> str | None:
    """Récupère la DATABASE_URL du connector SQL actif de l'org."""
    connector = Connector.query.filter_by(
        organization_id=org_id,
        type='sql',
        status='active',
        deleted_at=None
    ).first()

    if not connector:
        return None

    creds = ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None
    ).first()

    if not creds:
        return None

    return encryption_service.decrypt(creds.encrypted_token)


def _get_drive_connector_for_org(org_id: str) -> ConnectorCredentials | None:
    """Récupère les credentials Google Drive de l'org."""
    connector = Connector.query.filter_by(
        organization_id=org_id,
        type='google_drive',
        status='active',
        deleted_at=None
    ).first()

    if not connector:
        return None

    return ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None
    ).first()


def _get_dropbox_connector_for_org(org_id: str) -> ConnectorCredentials | None:
    """RÃ©cupÃ¨re les credentials Dropbox de l'org."""
    connector = Connector.query.filter_by(
        organization_id=org_id,
        type='dropbox',
        status='active',
        deleted_at=None
    ).first()

    if not connector:
        return None

    return ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None
    ).first()


# ============================================================================
# SERVERS STATUS
# ============================================================================

@mcp_bp.route('/servers/status', methods=['GET'])
async def servers_status():
    """Vérifie l'état des MCP servers Docker."""
    status = {}
    for connector_type, url in MCP_SERVERS.items():
        client = MCPHttpClient(url)
        status[connector_type] = {
            'url': url,
            'healthy': await client.health()
        }
    return jsonify({'status': 'success', 'servers': status})


# ============================================================================
# SQL
# ============================================================================

@mcp_bp.route('/database/tables', methods=['GET'])
async def list_tables():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    try:
        database_url = _get_database_url_for_org(org_id)
        if not database_url:
            return jsonify({'error': 'No SQL connector configured for this organization'}), 404
        client = get_mcp_client('sql')
        result = await client.show_tables(database_url=database_url)
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"list_tables error: {e}")
        return jsonify({'error': str(e)}), 502


@mcp_bp.route('/database/query', methods=['POST'])
async def query_database():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}
    sql_query = data.get('sql_query')
    if not sql_query:
        return jsonify({'error': 'sql_query required'}), 400
    try:
        database_url = _get_database_url_for_org(org_id)
        if not database_url:
            return jsonify({'error': 'No SQL connector configured for this organization'}), 404
        client = get_mcp_client('sql')
        result = await client.query_database(
            sql_query,
            data.get('limit', 1000),
            database_url=database_url
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"query_database error: {e}")
        return jsonify({'error': str(e)}), 502


@mcp_bp.route('/database/schema', methods=['GET'])
async def describe_table():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    table = request.args.get('table')
    if not table:
        return jsonify({'error': 'table param required'}), 400
    try:
        database_url = _get_database_url_for_org(org_id)
        if not database_url:
            return jsonify({'error': 'No SQL connector configured for this organization'}), 404
        client = get_mcp_client('sql')
        result = await client.describe_table(table, database_url=database_url)
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"describe_table error: {e}")
        return jsonify({'error': str(e)}), 502


# ============================================================================
# GOOGLE DRIVE
# ============================================================================

@mcp_bp.route('/drive/files', methods=['GET'])
async def list_drive_files():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    try:
        creds = _get_drive_connector_for_org(org_id)
        if not creds:
            return jsonify({'error': 'No Google Drive connector configured for this organization'}), 404

        client = get_mcp_client('google_drive')
        result = await client.list_documents(
            folder_id=request.args.get('parent_id'),
            max_results=request.args.get('max_results', 50, type=int),
            access_token=creds.encrypted_token
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"list_drive_files error: {e}")
        return jsonify({'error': str(e)}), 502


@mcp_bp.route('/drive/search', methods=['GET'])
async def search_drive():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'q param required'}), 400
    try:
        creds = _get_drive_connector_for_org(org_id)
        if not creds:
            return jsonify({'error': 'No Google Drive connector configured for this organization'}), 404

        client = get_mcp_client('google_drive')
        result = await client.search_files(query, access_token=creds.encrypted_token)
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"search_drive error: {e}")
        return jsonify({'error': str(e)}), 502


# ============================================================================
# DROPBOX
# ============================================================================
def _get_connector_credentials(org_id: str, connector_type: str) -> ConnectorCredentials | None:
    connector = Connector.query.filter_by(
        organization_id=org_id,
        type=connector_type,
        status='active',
        deleted_at=None
    ).first()
    if not connector:
        return None
    
    return ConnectorCredentials.query.filter_by(
        connector_id=connector.id,
        deleted_at=None
    ).first()

@mcp_bp.route('/dropbox/files', methods=['GET'])
async def list_dropbox_files():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    try:
        creds = _get_connector_credentials(org_id, 'dropbox')
        if not creds:
            return jsonify({'error': 'No Dropbox connector configured for this organization'}), 404

        access_token = encryption_service.decrypt(creds.encrypted_token)
        client = get_mcp_client('dropbox')
        result = await client.list_dropbox_files(
            path=request.args.get('path', ''),
            recursive=request.args.get('recursive', 'false').lower() == 'true',
            limit=request.args.get('limit', 50, type=int),
            bearer_token=access_token
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"list_dropbox_files error: {e}")
        return jsonify({'error': str(e)}), 502


@mcp_bp.route('/dropbox/search', methods=['GET'])
async def search_dropbox():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'q param required'}), 400
    try:
        creds = _get_connector_credentials(org_id, 'dropbox')
        if not creds:
            return jsonify({'error': 'No Dropbox connector configured for this organization'}), 404
        access_token = encryption_service.decrypt(creds.encrypted_token)
        client = get_mcp_client('dropbox')
        result = await client.search_dropbox_files(
            query,
            path=request.args.get('path', ''),
            limit=request.args.get('limit', 20, type=int),
            bearer_token=access_token
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"search_dropbox error: {e}")
        return jsonify({'error': str(e)}), 502


@mcp_bp.route('/dropbox/download', methods=['POST'])
async def download_dropbox_file_text():
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}
    path = data.get('path')
    if not path:
        return jsonify({'error': 'path required'}), 400
    try:
        creds = _get_connector_credentials(org_id, 'dropbox')
        if not creds:
            return jsonify({'error': 'No Dropbox connector configured for this organization'}), 404

        access_token = encryption_service.decrypt(creds.encrypted_token)
        client = get_mcp_client('dropbox')
        result = await client.download_dropbox_file_text(path, bearer_token=access_token)
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        logger.error(f"download_dropbox_file_text error: {e}")
        return jsonify({'error': str(e)}), 502

# ============================================================================
# INGESTION
# ============================================================================

@mcp_bp.route('/ingest/<connector_id>', methods=['POST'])
async def trigger_ingestion(connector_id: str):
    """Trigger ingestion for a specific connector."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    try:
        from ai.agents.office_manager.ingestion.tasks import trigger_ingestion_for_connector
        task = trigger_ingestion_for_connector.delay(
            connector_id=connector_id,
            org_id=org_id
        )
        return jsonify({
            'status': 'queued',
            'task_id': task.id,
            'message': f'Ingestion started for connector {connector_id}'
        })
    except Exception as e:
        logger.error(f"trigger_ingestion error: {e}")
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/ingest/status/<task_id>', methods=['GET'])
async def ingestion_status(task_id: str):
    """Check ingestion task status."""
    try:
        from celery_app import celery_app
        task = celery_app.AsyncResult(task_id)
        return jsonify({
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.ready() else None,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
