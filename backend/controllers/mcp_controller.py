"""
MCP Controller — Flask routes for MCP server interactions.
Connects Flask to shared MCP Docker servers via HTTP.
Supports multi-org connector management.
"""

import json
import logging
from datetime import datetime
from flask import g, request, jsonify, Blueprint, Response, stream_with_context
from services.mcp_http_client import get_mcp_client, MCP_SERVERS, MCPHttpClient
from models.connector import Connector, ConnectorCredentials
from models.conversation import Conversation, Message
from config.extensions import db
from services.encryption_service import get_encryption_service
from services.request_context import current_organization_id, current_user_id

logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')


@mcp_bp.before_request
def _authenticate_mcp():
    """Même exigence que /api/v2 : ce blueprint expose les credentials connecteurs.

    mcp_bp est enregistré séparément (routes/__init__.py), donc le before_request
    de api_bp ne le couvre pas — sans ceci il resterait entièrement ouvert.
    """
    from services.auth_service import AuthService
    from services.firebase_auth import FirebaseAuthError, extract_bearer_token, verify_token
    from services import locator

    if request.method == 'OPTIONS':
        return None

    token = extract_bearer_token(request.headers.get('Authorization'))
    if not token:
        return jsonify({'error': 'Authentification requise'}), 401

    try:
        claims = verify_token(token)
    except FirebaseAuthError as exc:
        logger.warning('Token /api/mcp rejeté : %s', exc)
        return jsonify({'error': 'Token invalide ou expiré'}), 401

    auth_service = AuthService(locator)
    user = auth_service.get_by_firebase_uid(claims.get('uid'))
    if not user:
        return jsonify({'error': 'Compte non provisionné', 'code': 'user_not_provisioned'}), 403

    g.firebase_claims = claims
    g.current_user = user

    member_orgs = auth_service.organization_ids_for(user)
    g.member_org_ids = member_orgs
    requested_org = request.headers.get('X-Organization-Id')
    if requested_org:
        if requested_org not in member_orgs:
            return jsonify({'error': 'Accès refusé à cette organisation'}), 403
        g.current_organization_id = requested_org
    else:
        g.current_organization_id = next(iter(member_orgs), None)

    return None


@mcp_bp.after_request
def _audit(response):
    """Trace every mutating /api/mcp call (searches, connector ops) in the audit log."""
    from services.audit import audit_request
    return audit_request(response)


# ============================================================================
# HELPERS
# ============================================================================

def _get_org_id() -> str | None:
    """Organisation courante, validée contre les memberships par _authenticate_mcp."""
    return current_organization_id()


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

    return get_encryption_service().decrypt(creds.encrypted_token)


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

        access_token = get_encryption_service().decrypt(creds.encrypted_token)
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
        access_token = get_encryption_service().decrypt(creds.encrypted_token)
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

        access_token = get_encryption_service().decrypt(creds.encrypted_token)
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

# ============================================================================
# ENTERPRISE SEARCH (SearchAgent)
# ============================================================================
"""@mcp_bp.route('/search', methods=['POST'])
def enterprise_search():
    Run the SearchAgent (LangGraph multi-step) for an org.
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400

    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'query is required'}), 400

    context = data.get('context', {})
    try:
        from ai.agents.office_manager.sub_agents.search_agent import SearchAgent
        agent = SearchAgent(org_id=org_id)
        result = agent.search(query=query, context=context)
        return jsonify({
            'status': 'success',
            'answer': result.get('answer', ''),
            'citations': result.get('citations', []),
            'execution_trace': result.get('execution_trace', []),
        })
    except Exception as e:
        logger.exception("Enterprise search failed for org %s", org_id)
        return jsonify({'error': str(e)}), 500"""

@mcp_bp.route('/search', methods=['POST'])
def enterprise_search():
    """Enterprise Search Agent endpoint.

    Sync view on purpose: run_search (LangGraph) is synchronous, so an async view
    only pulls in Flask's optional `async` extra for nothing — and its absence was
    500'ing this route ("Install Flask with the 'async' extra").
    """
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400

    data  = request.get_json() or {}
    query = data.get('query')
    if not query:
        return jsonify({'error': 'query required'}), 400

    try:
        from ai.agents.search.graph import run_search
        result = run_search(
            query=query,
            org_id=org_id,
            user_role=data.get('user_role', 'employee'),
            allowed_connectors=data.get('allowed_connectors'),
            scope_connector_id=data.get('connector_id'),
        )
        return jsonify({'status': 'success', **result})
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _save_assistant_message(conversation_id, answer: str, meta: dict) -> None:
    """Persist the assistant turn (answer + structured result) at stream end."""
    try:
        db.session.add(Message(
            conversation_id=conversation_id,
            role='assistant',
            content=answer,
            message_metadata={
                'generated_sql': meta.get('generated_sql', ''),
                'sql_columns':   meta.get('sql_columns', []),
                'sql_rows':      meta.get('sql_rows', []),
                'sources':       meta.get('sources', []),
            },
        ))
        convo = Conversation.query.get(conversation_id)
        if convo:
            convo.updated_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to persist assistant message: %s", e)


@mcp_bp.route('/search-stream', methods=['POST'])
def enterprise_search_stream():
    """SSE variant of /search — streams the answer token-by-token, with history.

    Emits `conversation` (the id) first, then `meta` (SQL + rows + sources) so the
    grid fills, then `token` events for the answer, then `done`. Persists both the
    user and assistant turns so the conversation can be reopened and continued;
    prior turns are passed back in so follow-up questions resolve. stream_with_context
    keeps the app context alive so DB access works during iteration.
    """
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}
    query = data.get('query')
    if not query:
        return jsonify({'error': 'query required'}), 400

    from ai.agents.search.graph import run_search_stream

    user_id = current_user_id()

    # Resolve or open the conversation, and gather prior turns for follow-up context.
    conversation_id = data.get('conversation_id')
    history: list = []
    convo = None
    if conversation_id:
        convo = Conversation.query.filter_by(
            id=conversation_id, organization_id=org_id, deleted_at=None,
        ).first()
    if convo is None:
        convo = Conversation(
            organization_id=org_id, user_id=user_id, title=query[:80],
        )
        db.session.add(convo)
        db.session.commit()
    else:
        prior = Message.query.filter_by(conversation_id=convo.id, deleted_at=None) \
            .order_by(Message.created_at.asc()).all()
        history = [{"role": m.role, "content": m.content or ""} for m in prior]

    conv_id = str(convo.id)
    # Persist the user turn now (survives an early client disconnect).
    db.session.add(Message(conversation_id=convo.id, role='user', content=query))
    convo.updated_at = datetime.utcnow()
    db.session.commit()

    def sse():
        yield f"event: conversation\ndata: {json.dumps({'conversation_id': conv_id})}\n\n"
        answer_parts: list[str] = []
        meta_payload: dict = {}
        try:
            for event, payload in run_search_stream(
                query=query,
                org_id=org_id,
                user_role=data.get('user_role', 'employee'),
                allowed_connectors=data.get('allowed_connectors'),
                scope_connector_id=data.get('connector_id'),
                history=history,
            ):
                if event == 'meta':
                    meta_payload = payload
                elif event == 'token':
                    answer_parts.append(payload)
                yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
            _save_assistant_message(convo.id, "".join(answer_parts), meta_payload)
        except Exception as e:
            logger.error("search-stream failed: %s", e, exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(sse()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',   # disable proxy buffering (nginx/Render)
            'Connection': 'keep-alive',
        },
    )


@mcp_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """Recent conversations of the current user in this org (newest first)."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    uid = current_user_id()
    convos = Conversation.query.filter_by(
        organization_id=org_id, user_id=uid, deleted_at=None,
    ).order_by(Conversation.updated_at.desc()).limit(50).all()
    return jsonify({'data': [
        {
            'id': str(c.id),
            'title': c.title,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convos
    ]})


@mcp_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """A conversation with its messages (to reopen and continue it)."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    convo = Conversation.query.filter_by(
        id=conversation_id, organization_id=org_id, user_id=current_user_id(), deleted_at=None,
    ).first()
    if not convo:
        return jsonify({'error': 'not found'}), 404
    msgs = Message.query.filter_by(conversation_id=convo.id, deleted_at=None) \
        .order_by(Message.created_at.asc()).all()
    return jsonify({
        'id': str(convo.id),
        'title': convo.title,
        'messages': [
            {'role': m.role, 'content': m.content, 'metadata': m.message_metadata or {}}
            for m in msgs
        ],
    })


@mcp_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    convo = Conversation.query.filter_by(
        id=conversation_id, organization_id=org_id, user_id=current_user_id(), deleted_at=None,
    ).first()
    if not convo:
        return jsonify({'error': 'not found'}), 404
    convo.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'deleted': True})


@mcp_bp.route('/sql/run', methods=['POST'])
def sql_run():
    """Execute raw SQL typed directly in the query form. Read-only (SELECT/WITH)
    here — writes must go through /write/preview + /write/confirm."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}
    sql = (data.get('sql') or '').strip()
    if not sql:
        return jsonify({'error': 'sql required'}), 400

    from services.sql_write import statement_kind
    from ai.agents.search.nodes.sql_query import (
        _resolve_sql_connector, _decrypt_connector_url, _call_sql_tool,
        _is_safe_select, _org_plan_limits, MAX_RESULT_ROWS,
    )

    kind = statement_kind(sql)
    if kind == 'write':
        return jsonify({'ok': False, 'error': "Requête d'écriture — passe par la confirmation.",
                        'code': 'write_requires_confirmation'}), 409
    if kind != 'read' or not _is_safe_select(sql):
        return jsonify({'ok': False, 'error': "Seules les requêtes SELECT / WITH (lecture) sont exécutées ici."}), 400

    connector = _resolve_sql_connector(org_id, data.get('connector_id'))
    if not connector:
        return jsonify({'ok': False, 'error': 'No active SQL connector'}), 404
    db_url = _decrypt_connector_url(connector)
    limits = _org_plan_limits(org_id)
    try:
        result = _call_sql_tool(
            "query_database",
            {"sql_query": sql, "limit": limits.get("max_rows", MAX_RESULT_ROWS)},
            db_url,
        )
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    if result.get("status") != "success":
        return jsonify({'ok': False, 'error': result.get("message", "Query failed"), 'sql': sql})
    return jsonify({'ok': True, 'sql': sql,
                    'columns': result.get("columns", []), 'rows': result.get("rows", [])})


@mcp_bp.route('/write/preview', methods=['POST'])
def write_preview():
    """Phase 1 — propose a write and preview its impact WITHOUT committing.
    Guards the statement, then dry-runs it in a rolled-back transaction."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}

    from services.sql_write import guard_write, generate_write_sql, MASS_WRITE_THRESHOLD
    from services.audit import record
    from config.plans import plan_allows
    from models.organization import Organization
    from uuid import UUID
    from ai.agents.search.nodes.sql_query import (
        _resolve_sql_connector, _decrypt_connector_url, _call_sql_tool,
        _org_plan_limits, _fetch_schema_smart,
    )

    org = Organization.query.get(UUID(org_id))
    if not plan_allows(org.plan if org else None, 'writes'):
        return jsonify({'ok': False, 'code': 'plan_required',
                        'error': "Les écritures nécessitent le plan Business ou supérieur."}), 403

    connector = _resolve_sql_connector(org_id, data.get('connector_id'))
    if not connector:
        return jsonify({'ok': False, 'error': 'No active SQL connector'}), 404
    db_url = _decrypt_connector_url(connector)
    limits = _org_plan_limits(org_id)

    sql = (data.get('sql') or '').strip()
    if not sql:
        query = (data.get('query') or '').strip()
        if not query:
            return jsonify({'ok': False, 'error': 'query or sql required'}), 400
        schema = _fetch_schema_smart(connector, query, db_url, limits)
        sql = generate_write_sql(query, schema, limits['sql_model'])
    if not sql:
        return jsonify({'ok': False, 'error': "Impossible de produire une écriture sûre pour cette demande."})

    ok, err = guard_write(sql)
    if not ok:
        record(action='denied', resource='write.preview', tool='sql-write',
               metadata={'sql': sql, 'reason': err})
        return jsonify({'ok': False, 'error': err, 'sql': sql})

    try:
        result = _call_sql_tool("execute_write", {"sql_query": sql, "dry_run": True}, db_url)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'sql': sql})
    if result.get("status") != "success":
        return jsonify({'ok': False, 'error': result.get("message", "dry-run failed"), 'sql': sql})

    affected = result.get("rows_affected")
    record(action='read', resource='write.preview', tool='sql-write',
           metadata={'sql': sql, 'rows_affected': affected, 'connector_id': str(connector.id)})
    return jsonify({
        'ok': True, 'sql': sql, 'rows_affected': affected,
        'requires_extra_confirm': bool(affected and affected > MASS_WRITE_THRESHOLD),
        'connector_id': str(connector.id),
    })


@mcp_bp.route('/write/confirm', methods=['POST'])
def write_confirm():
    """Phase 2 — execute the confirmed write (committed). Re-guards + re-gates."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json() or {}
    sql = (data.get('sql') or '').strip()
    if not sql:
        return jsonify({'ok': False, 'error': 'sql required'}), 400

    from services.sql_write import guard_write
    from services.audit import record
    from config.plans import plan_allows
    from models.organization import Organization
    from uuid import UUID
    from ai.agents.search.nodes.sql_query import (
        _resolve_sql_connector, _decrypt_connector_url, _call_sql_tool,
    )

    org = Organization.query.get(UUID(org_id))
    if not plan_allows(org.plan if org else None, 'writes'):
        return jsonify({'ok': False, 'code': 'plan_required',
                        'error': "Les écritures nécessitent le plan Business ou supérieur."}), 403

    ok, err = guard_write(sql)
    if not ok:
        record(action='denied', resource='write.confirm', tool='sql-write',
               metadata={'sql': sql, 'reason': err})
        return jsonify({'ok': False, 'error': err})

    connector = _resolve_sql_connector(org_id, data.get('connector_id'))
    if not connector:
        return jsonify({'ok': False, 'error': 'No active SQL connector'}), 404
    db_url = _decrypt_connector_url(connector)

    try:
        result = _call_sql_tool("execute_write", {"sql_query": sql, "dry_run": False}, db_url)
    except Exception as e:
        record(action='update', resource='write.confirm', tool='sql-write',
               metadata={'sql': sql, 'outcome': 'error', 'error': str(e)})
        return jsonify({'ok': False, 'error': str(e), 'sql': sql})
    if result.get("status") != "success":
        record(action='update', resource='write.confirm', tool='sql-write',
               metadata={'sql': sql, 'outcome': 'error', 'error': result.get('message')})
        return jsonify({'ok': False, 'error': result.get("message", "execution failed"), 'sql': sql})

    affected = result.get("rows_affected")
    record(action='update', resource='write.confirm', tool='sql-write',
           metadata={'sql': sql, 'rows_affected': affected, 'outcome': 'committed',
                     'connector_id': str(connector.id)})
    return jsonify({'ok': True, 'sql': sql, 'rows_affected': affected, 'committed': True})


@mcp_bp.route('/db-insights', methods=['POST'])
def db_insights():
    """Background DB analysis: inferred business domain, anticipated questions,
    and a deterministic Mermaid ER diagram of the connector's schema."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    data = request.get_json(silent=True) or {}
    try:
        from ai.agents.db_analysis import get_db_insights
        result = get_db_insights(org_id, data.get('connector_id'))
        return jsonify({'status': 'success', **result})
    except Exception as e:
        logger.error("DB insights error: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


# KNOWLEDGE GRAPH
# ============================================================================
@mcp_bp.route('/knowledge-graph/build', methods=['POST'])
async def build_knowledge_graph_endpoint():
    """Trigger KG build for an org."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    try:
        from ai.agents.office_manager.ingestion.tasks import build_knowledge_graph
        task = build_knowledge_graph.delay(org_id=org_id)
        return jsonify({
            'status': 'queued',
            'task_id': task.id,
            'message': f'KG build started for org {org_id}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mcp_bp.route('/knowledge-graph/search', methods=['GET'])
async def search_knowledge_graph():
    """Semantic search across the org KG."""
    org_id = _get_org_id()
    if not org_id:
        return jsonify({'error': 'X-Organization-Id header required'}), 400
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'q param required'}), 400
    node_types = request.args.getlist('type')
    try:
        from ai.knowledge.knowledge_graph_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder(org_id)
        nodes = builder.semantic_search(query, node_types or None, limit=10)
        return jsonify({
            'status': 'success',
            'results': [
                {
                    'id': str(n.id),
                    'type': n.node_type,
                    'name': n.name,
                    'connector': n.connector_type,
                    'metadata': n.kgnode_metadata,
                }
                for n in nodes
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
