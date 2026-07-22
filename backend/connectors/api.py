"""Connectors REST API — exposes endpoints for all MCP connector types.

Routes are registered on the shared api_bp Blueprint (prefix /api/v2).

Endpoints
---------
  GET    /connectors                         list connectors for an organisation
  POST   /connectors                         create a new connector
  GET    /connectors/<id>                    get a connector
  PUT    /connectors/<id>                    update connector name / status
  DELETE /connectors/<id>                    soft-delete a connector

  POST   /connectors/<id>/test               test the MCP server connection
  POST   /connectors/<id>/sync               trigger a full sync
  GET    /connectors/<id>/tools              list tools exposed by the MCP server
  POST   /connectors/<id>/tools/call         call a specific tool
  GET    /connectors/<id>/resources          list resources known to the MCP server
  GET    /connectors/<id>/resources/local    list resources stored in the local DB

  # Google Drive extras
  GET    /connectors/<id>/gdrive/search      search files (query param: q)
  POST   /connectors/<id>/gdrive/export      export a file to plain text

  # Dropbox extras
  GET    /connectors/<id>/dropbox/files      list files (query param: path)
  GET    /connectors/<id>/dropbox/search     search files (query param: q)
  POST   /connectors/<id>/dropbox/download   download a file as text

  # SharePoint extras
  GET    /connectors/<id>/sharepoint/sites           list sites
  GET    /connectors/<id>/sharepoint/libraries       list libraries (query param: site_id)
  GET    /connectors/<id>/sharepoint/search          search documents (query param: q)

  # SQL extras
  POST   /connectors/<id>/sql/query          execute a read-only query
  GET    /connectors/<id>/sql/tables         list tables
  GET    /connectors/<id>/sql/schema         get full schema
  GET    /connectors/<id>/sql/describe       describe a table (query param: table)
"""
import logging
from uuid import UUID

from flask import request, jsonify
from sqlalchemy import func

from services import locator
from models.connector import Connector, ConnectorCredentials
import connectors as connector_registry
from services.encryption_service import get_encryption_service
from services.request_context import current_organization_id as get_current_organization_id

logger = logging.getLogger(__name__)

# OAuth connectors only have usable credentials AFTER their OAuth callback,
# so their ingestion is started there — not at connector-creation time.
OAUTH_CONNECTOR_TYPES = {"google_drive", "sharepoint", "dropbox"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connector_to_dict(c: Connector) -> dict:
    return {
        "id": str(c.id),
        "organization_id": str(c.organization_id),
        "type": c.type,
        "engine": c.engine,
        "name": c.name,
        "status": c.status,
        "connection_mode": getattr(c, "connection_mode", "cloud"),
        "hide_audit_tables": bool(getattr(c, "hide_audit_tables", True)),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "schema_crawl_status": c.schema_crawl_status,
        "schema_table_count": c.schema_table_count,
    }


def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _resolve_sql_token(data: dict) -> str | None:
    """Assemble l'URL de connexion d'un connecteur SQL.

    Priorité aux champs structurés (host/port/user/password…) façon DBeaver ; à
    défaut, un `token` (URL brute) est accepté pour compatibilité. Renvoie None si
    rien n'est fourni (édition qui ne change pas les identifiants).
    """
    connection = data.get("connection")
    engine = data.get("engine")
    if connection and engine:
        from services.db_url import build_database_url
        return build_database_url(
            engine,
            host=connection.get("host"),
            port=connection.get("port"),
            database=connection.get("database"),
            username=connection.get("username"),
            password=connection.get("password"),
            service_name=connection.get("service_name"),
            ssl=connection.get("ssl"),
        )
    return data.get("token")


def _friendly_db_error(raw: str) -> str:
    """Traduit une erreur brute de pilote SQL en message actionnable.

    Les erreurs de connexion cloud tournent presque toujours autour de 3 causes :
    joignabilité (pare-feu / IP non whitelistées), SSL, ou identifiants. On mappe
    les signatures connues vers un conseil clair et on renvoie le brut sinon.
    """
    r = (raw or "").lower()
    reach = ("timed out", "timeout", "could not connect", "connection refused",
             "can't connect", "name or service not known", "could not translate host")
    ssl_sigs = ("ssl", "no encryption", "server does not support ssl")
    auth_sigs = ("password authentication failed", "access denied",
                 "login failed", "authentication failed")
    db_sigs = ("does not exist", "unknown database", "database not found")

    if not r or any(s in r for s in reach):
        return ("Base injoignable (timeout/refus). Vérifie l'hôte et le port, et "
                "autorise les IP de sortie de Render dans le pare-feu de la base.")
    if any(s in r for s in ssl_sigs):
        return "La base exige SSL. Coche l'option « Connexion SSL » et réessaie."
    if any(s in r for s in auth_sigs):
        return "Identifiants refusés — vérifie l'utilisateur et le mot de passe."
    if any(s in r for s in db_sigs):
        return "Base ou schéma introuvable — vérifie le nom de la base."
    return raw.strip() or "Connexion échouée."


def _connector_progress(connector_id) -> dict:
    """Ingestion completion for a connector.

    Combines resource-level status counts with the latest sync's batch progress
    so the UI can render a "% terminé" ring that animates during a run.
    """
    from config.extensions import db
    from models.resource import Resource
    from models.connector import ConnectorSync

    cid = connector_id if isinstance(connector_id, UUID) else UUID(str(connector_id))

    rows = (
        db.session.query(Resource.ingestion_status, func.count(Resource.id))
        .filter(Resource.connector_id == cid, Resource.deleted_at.is_(None))
        .group_by(Resource.ingestion_status)
        .all()
    )
    counts = {status: n for status, n in rows}
    total      = sum(counts.values())
    done       = counts.get('done', 0)
    skipped    = counts.get('skipped', 0)
    failed     = counts.get('failed', 0)
    processing = counts.get('processing', 0)
    pending    = counts.get('pending', 0)
    finished   = done + skipped + failed

    sync = (
        db.session.query(ConnectorSync)
        .filter(ConnectorSync.connector_id == cid)
        .order_by(ConnectorSync.started_at.desc())
        .first()
    )
    run_status = sync.status if sync else 'idle'

    if run_status == 'running':
        # Batch progress is the most reliable signal while resources are still
        # being created; fall back to resource ratio. Cap below 100 until done.
        if sync and sync.total_batches:
            percent = round(100 * (sync.batches_completed or 0) / sync.total_batches)
        elif total:
            percent = round(100 * finished / total)
        else:
            percent = 0
        percent = min(percent, 99)
    elif run_status == 'completed' or (total and finished >= total):
        percent = 100 if total else 0
    else:  # 'failed' or 'idle'
        percent = round(100 * finished / total) if total else 0

    return {
        "percent": percent,
        "status": run_status,
        "total": total,
        "done": done,
        "skipped": skipped,
        "failed": failed,
        "processing": processing,
        "pending": pending,
    }


def _get_connector_or_404(connector_id: str):
    c = locator.connectors.get_by_id(UUID(connector_id))
    if not c:
        return None, _err(f"Connector '{connector_id}' not found", 404)
    return c, None


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register(api_bp) -> None:  # noqa: C901

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api_bp.route("/connectors", methods=["GET"])
    def list_connectors():
        org_id = get_current_organization_id()
        if not org_id:
            return _err("Aucune organisation associée à ce compte")
        items = locator.connectors.list_by_organization(UUID(org_id))
        data = []
        for c in items:
            d = _connector_to_dict(c)
            try:
                d["progress"] = _connector_progress(c.id)
            except Exception as exc:
                logger.warning("progress failed for connector %s: %s", c.id, exc)
                d["progress"] = None
            data.append(d)
        return jsonify({"data": data})

    @api_bp.route("/connectors", methods=["POST"])
    def create_connector():
        data = request.get_json() or {}
        # L'organisation vient du contexte authentifié. Auparavant le corps de la
        # requête pouvait imposer n'importe quel organization_id — soit un connecteur
        # créable dans le tenant d'autrui.
        org_id = get_current_organization_id()
        connector_type = data.get("type")
        name = data.get("name")
        engine = data.get("engine")

        if not org_id:
            return _err("Aucune organisation associée à ce compte")
        if connector_type not in connector_registry.CONNECTOR_TYPES:
            return _err(f"type must be one of {connector_registry.CONNECTOR_TYPES}")
        if not name:
            return _err("name required")

        # 'local' → an on-prem dial-home agent holds the credentials; the cloud
        # stores none and reaches the DB through the agent gateway.
        connection_mode = "local" if data.get("connection_mode") == "local" else "cloud"

        token = None
        if connection_mode == "cloud":
            try:
                token = _resolve_sql_token(data)
            except ValueError as exc:
                return _err(str(exc))

        connector = Connector(
            organization_id=UUID(org_id),
            type=connector_type,
            engine=engine,
            name=name,
            status="active",
            connection_mode=connection_mode,
        )
        connector = locator.connectors.create(connector)

        ingestion_task_id = None
        # Local connectors are crawled once their agent is online (via the sidebar
        # "sync schema" button) — the schema isn't reachable at creation time.
        if connection_mode == "local":
            payload = _connector_to_dict(connector)
            payload["ingestion_task_id"] = None
            return jsonify(payload), 201

        if token:
            creds = ConnectorCredentials(
                connector_id=connector.id,
                encrypted_token=get_encryption_service().encrypt(token),
            )
            locator.connector_credentials.create(creds)

            # SQL connectors: a database agent queries the data live (Text-to-SQL),
            # so we only crawl the *schema* catalog — no document ingestion of the
            # rows (that path stays for file connectors only).
            if connector_type == "sql":
                from ai.agents.office_manager.ingestion.tasks import start_schema_crawl
                start_schema_crawl(connector.id, org_id)
            elif connector_type not in OAUTH_CONNECTOR_TYPES:
                # Non-OAuth, non-SQL connectors (if any) have usable credentials
                # now, so kick off document ingestion. OAuth ones start in their
                # callback.
                from ai.agents.office_manager.ingestion.tasks import start_ingestion
                ingestion_task_id = start_ingestion(connector.id, org_id)

        payload = _connector_to_dict(connector)
        payload["ingestion_task_id"] = ingestion_task_id
        return jsonify(payload), 201

    @api_bp.route("/connectors/<connector_id>", methods=["GET"])
    def get_connector(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        return jsonify(_connector_to_dict(connector))

    @api_bp.route("/connectors/<connector_id>", methods=["PUT"])
    def update_connector(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        data = request.get_json() or {}
        if "name" in data:
            connector.name = data["name"]
        if "status" in data:
            connector.status = data["status"]
        if "engine" in data:
            connector.engine = data["engine"]
        locator.connectors.update(connector)

        # Optionally rotate the stored credential (structured fields or raw URL).
        try:
            token = _resolve_sql_token(data)
        except ValueError as exc:
            return _err(str(exc))
        if token:
            creds = locator.connector_credentials.get_by_connector(UUID(connector_id))
            if creds:
                creds.encrypted_token = get_encryption_service().encrypt(token)
                locator.connector_credentials.update(creds)
            else:
                locator.connector_credentials.create(
                    ConnectorCredentials(
                        connector_id=UUID(connector_id),
                        encrypted_token=get_encryption_service().encrypt(token),
                    )
                )

        return jsonify(_connector_to_dict(connector))

    @api_bp.route("/connectors/<connector_id>", methods=["DELETE"])
    def delete_connector(connector_id: str):
        deleted = locator.connectors.soft_delete(UUID(connector_id))
        if not deleted:
            return _err(f"Connector '{connector_id}' not found", 404)
        return jsonify({"deleted": True})

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/test-connection", methods=["POST"])
    def test_connection_presave():
        """Test a SQL connection BEFORE creating the connector.

        Takes the same structured `connection` fields as create (engine + host/
        port/database/user/password[/ssl]), assembles the URL and probes it via
        the SQL MCP server with a short timeout — so the user gets an immediate,
        clear verdict instead of discovering a bad connection 30s later in the
        ingestion logs. Nothing is persisted.
        """
        data = request.get_json() or {}
        try:
            token = _resolve_sql_token(data)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)})
        if not token:
            return jsonify({"ok": False, "error": "Renseigne les champs de connexion."})

        import httpx
        from services.mcp_http_client import MCP_SERVERS

        mcp_url = MCP_SERVERS.get("sql")
        try:
            resp = httpx.post(
                f"{mcp_url}/execute",
                json={"tool_name": "test_connection", "params": {}, "database_url": token},
                timeout=20,
            )
            if resp.status_code >= 400:
                # The MCP wraps connection failures as {"detail": "..."} (HTTP 500).
                try:
                    detail = resp.json().get("detail") or resp.text
                except Exception:
                    detail = resp.text
                return jsonify({"ok": False, "error": _friendly_db_error(detail)})

            result = resp.json()
            if result.get("status") == "success":
                return jsonify({
                    "ok": True,
                    "dialect": result.get("dialect"),
                    "table_count": result.get("table_count"),
                })
            return jsonify({"ok": False, "error": _friendly_db_error(result.get("message", ""))})
        except httpx.TimeoutException:
            return jsonify({"ok": False, "error": _friendly_db_error("timed out")})
        except Exception as exc:
            logger.error("test-connection failed: %s", exc, exc_info=True)
            return jsonify({"ok": False, "error": _friendly_db_error(str(exc))})

    @api_bp.route("/connectors/<connector_id>/test", methods=["POST"])
    def test_connector(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        try:
            service = connector_registry.get_service(connector.type, locator)
            ok = service.test_connection(connector_id)
            return jsonify({"connected": ok})
        except ValueError as exc:
            return _err(str(exc))

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/sync", methods=["POST"])
    def sync_connector(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        try:
            sync_job = connector_registry.get_sync(connector.type, locator)
            result = sync_job.run(connector_id)
            return jsonify(result.to_dict())
        except ValueError as exc:
            return _err(str(exc))

    @api_bp.route("/connectors/<connector_id>/agent-token", methods=["POST"])
    def connector_agent_token(connector_id: str):
        """Pairing token + one-line command to run the on-prem dial-home agent."""
        import os
        import jwt
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        secret = os.getenv("AGENT_TOKEN_SECRET", "")
        if not secret:
            return _err("Agent non configuré (AGENT_TOKEN_SECRET manquant)", 503)
        token = jwt.encode(
            {"connector_id": str(connector.id), "org_id": str(connector.organization_id)},
            secret, algorithm="HS256",
        )
        gateway = os.getenv("AGENT_GATEWAY_PUBLIC_URL", "wss://flexianalyse-gateway.onrender.com/agent")
        image = os.getenv("AGENT_IMAGE", "flexianalyse/agent:latest")
        command = (
            'docker run -d --name flexianalyse-agent '
            '-e FLEXI_AGENT_MODE=1 '
            f'-e FLEXI_TOKEN="{token}" '
            f'-e FLEXI_GATEWAY_URL="{gateway}" '
            '-e DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME" '
            f'{image}'
        )
        return jsonify({"token": token, "command": command, "gateway": gateway})

    @api_bp.route("/connectors/<connector_id>/agent-status", methods=["GET"])
    def connector_agent_status(connector_id: str):
        """Whether the connector's on-prem agent is currently connected."""
        import os
        import httpx
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        gateway = os.getenv("AGENT_GATEWAY_URL", "http://localhost:3010").strip()
        if gateway and "://" not in gateway:
            gateway = f"http://{gateway}"
        try:
            r = httpx.get(f"{gateway}/status/{connector.id}", timeout=5)
            return jsonify({"online": bool(r.json().get("online"))})
        except Exception:
            return jsonify({"online": False})

    @api_bp.route("/connectors/<connector_id>/schema/crawl", methods=["POST"])
    def crawl_connector_schema_route(connector_id: str):
        """(Re)crawl the SQL schema catalog used by Text-to-SQL retrieval."""
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sql":
            return _err("Connector is not of type sql", 409)
        from ai.agents.office_manager.ingestion.tasks import start_schema_crawl
        task_id = start_schema_crawl(connector.id, str(connector.organization_id))
        if not task_id:
            return _err("Failed to start schema crawl (is the Celery worker running?)", 503)
        return jsonify({"status": "started", "task_id": task_id})

    @api_bp.route("/connectors/<connector_id>/audit-tables", methods=["PATCH"])
    def set_hide_audit_tables(connector_id: str):
        """Toggle whether audit/log/system tables are hidden from the diagram and
        excluded from Text-to-SQL retrieval for this connector."""
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        data = request.get_json(silent=True) or {}
        hide = data.get("hide")
        if not isinstance(hide, bool):
            return _err("Body must include boolean 'hide'", 400)
        from config.extensions import db
        connector.hide_audit_tables = hide
        db.session.commit()
        return jsonify(_connector_to_dict(connector))

    @api_bp.route("/connectors/<connector_id>/ingest", methods=["POST"])
    def ingest_connector(connector_id: str):
        """Launch the full document ingestion pipeline (download → extract → embed
        → KG) for a file connector. This is what the sidebar 'sync' button calls.

        SQL connectors don't use document ingestion (the agent queries the data
        live) — they use the schema crawl instead, so route them there.
        """
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        from ai.agents.office_manager.ingestion.tasks import start_ingestion, start_schema_crawl
        if connector.type == "sql":
            task_id = start_schema_crawl(connector.id, str(connector.organization_id))
            if not task_id:
                return _err("Failed to start schema crawl (is the Celery worker running?)", 503)
            return jsonify({"status": "started", "schema_crawl": True, "task_id": task_id})
        task_id = start_ingestion(connector.id, str(connector.organization_id))
        if not task_id:
            return _err("Failed to start ingestion (is the Celery worker running?)", 503)
        return jsonify({"status": "started", "ingestion_task_id": task_id})

    # ------------------------------------------------------------------
    # MCP tools
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/tools", methods=["GET"])
    def list_tools(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        try:
            service = connector_registry.get_service(connector.type, locator)
            tools = service.list_tools(connector_id)
            return jsonify({"data": tools})
        except Exception as exc:
            logger.error("list_tools error [%s]: %s", connector_id, exc, exc_info=True)
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/tools/call", methods=["POST"])
    def call_tool(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        data = request.get_json() or {}
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})
        if not tool_name:
            return _err("tool name required")
        try:
            service = connector_registry.get_service(connector.type, locator)
            result = service.call_tool(connector_id, tool_name, arguments)
            return jsonify(result)
        except Exception as exc:
            logger.error("call_tool error [%s/%s]: %s", connector_id, tool_name, exc, exc_info=True)
            return _err(str(exc), 502)

    # ------------------------------------------------------------------
    # MCP resources
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/resources", methods=["GET"])
    def list_mcp_resources(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        try:
            service = connector_registry.get_service(connector.type, locator)
            resources = service.list_resources(connector_id)
            return jsonify({"data": resources})
        except Exception as exc:
            logger.error("list_resources error [%s]: %s", connector_id, exc, exc_info=True)
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/resources/local", methods=["GET"])
    def list_local_resources(connector_id: str):
        _, err = _get_connector_or_404(connector_id)
        if err:
            return err
        items = locator.resources.list_by_connector(UUID(connector_id))
        return jsonify({"data": [
            {
                "id": str(r.id),
                "external_id": r.external_id,
                "type": r.type,
                "title": r.title,
                "metadata": r.ressource_metadata,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in items
        ]})

    @api_bp.route("/connectors/<connector_id>/progress", methods=["GET"])
    def connector_progress(connector_id: str):
        _, err = _get_connector_or_404(connector_id)
        if err:
            return err
        return jsonify({"data": _connector_progress(UUID(connector_id))})

    # ------------------------------------------------------------------
    # Google Drive extras
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/gdrive/search", methods=["GET"])
    def gdrive_search(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "google_drive":
            return _err("Connector is not of type google_drive", 409)
        query = request.args.get("q")
        if not query:
            return _err("query param 'q' required")
        try:
            from connectors.google_drive.service import GoogleDriveService
            svc = GoogleDriveService(locator)
            return jsonify(svc.search_files(connector_id, query))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/gdrive/export", methods=["POST"])
    def gdrive_export(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "google_drive":
            return _err("Connector is not of type google_drive", 409)
        data = request.get_json() or {}
        file_id = data.get("file_id")
        mime_type = data.get("mime_type", "text/plain")
        if not file_id:
            return _err("file_id required")
        try:
            from connectors.google_drive.service import GoogleDriveService
            svc = GoogleDriveService(locator)
            return jsonify(svc.export_file(connector_id, file_id, mime_type))
        except Exception as exc:
            return _err(str(exc), 502)

    # ------------------------------------------------------------------
    # Dropbox extras
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/dropbox/files", methods=["GET"])
    def dropbox_list_files(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "dropbox":
            return _err("Connector is not of type dropbox", 409)
        try:
            from connectors.dropbox.service import DropboxService
            svc = DropboxService(locator)
            return jsonify(
                svc.list_files(
                    connector_id,
                    path=request.args.get("path", ""),
                    recursive=request.args.get("recursive", "false").lower() == "true",
                    limit=request.args.get("limit", 50, type=int),
                )
            )
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/dropbox/search", methods=["GET"])
    def dropbox_search(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "dropbox":
            return _err("Connector is not of type dropbox", 409)
        query = request.args.get("q")
        if not query:
            return _err("query param 'q' required")
        try:
            from connectors.dropbox.service import DropboxService
            svc = DropboxService(locator)
            return jsonify(
                svc.search_files(
                    connector_id,
                    query,
                    path=request.args.get("path", ""),
                    limit=request.args.get("limit", 20, type=int),
                )
            )
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/dropbox/download", methods=["POST"])
    def dropbox_download(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "dropbox":
            return _err("Connector is not of type dropbox", 409)
        data = request.get_json() or {}
        path = data.get("path")
        if not path:
            return _err("path required")
        try:
            from connectors.dropbox.service import DropboxService
            svc = DropboxService(locator)
            return jsonify(svc.download_file_text(connector_id, path))
        except Exception as exc:
            return _err(str(exc), 502)

    # ------------------------------------------------------------------
    # SharePoint extras
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/sharepoint/sites", methods=["GET"])
    def sharepoint_list_sites(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sharepoint":
            return _err("Connector is not of type sharepoint", 409)
        try:
            from connectors.sharepoint.service import SharePointService
            svc = SharePointService(locator)
            return jsonify(svc.list_sites(connector_id))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/sharepoint/libraries", methods=["GET"])
    def sharepoint_list_libraries(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sharepoint":
            return _err("Connector is not of type sharepoint", 409)
        site_id = request.args.get("site_id")
        if not site_id:
            return _err("query param 'site_id' required")
        try:
            from connectors.sharepoint.service import SharePointService
            svc = SharePointService(locator)
            return jsonify(svc.list_libraries(connector_id, site_id))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/sharepoint/search", methods=["GET"])
    def sharepoint_search(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sharepoint":
            return _err("Connector is not of type sharepoint", 409)
        query = request.args.get("q")
        if not query:
            return _err("query param 'q' required")
        site_id = request.args.get("site_id")
        try:
            from connectors.sharepoint.service import SharePointService
            svc = SharePointService(locator)
            return jsonify(svc.search_documents(connector_id, query, site_id))
        except Exception as exc:
            return _err(str(exc), 502)

    # ------------------------------------------------------------------
    # SQL extras
    # ------------------------------------------------------------------

    @api_bp.route("/connectors/<connector_id>/sql/query", methods=["POST"])
    def sql_execute_query(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sql":
            return _err("Connector is not of type sql", 409)
        data = request.get_json() or {}
        query = data.get("query")
        if not query:
            return _err("query required")
        database = data.get("database")
        params = data.get("params")
        row_limit = int(data.get("row_limit", 500))
        try:
            from connectors.sql.service import SQLService
            svc = SQLService(locator)
            return jsonify(svc.execute_query(connector_id, query, database, params, row_limit))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/sql/tables", methods=["GET"])
    def sql_list_tables(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sql":
            return _err("Connector is not of type sql", 409)
        database = request.args.get("database")
        schema = request.args.get("schema", "public")
        try:
            from connectors.sql.service import SQLService
            svc = SQLService(locator)
            return jsonify(svc.list_tables(connector_id, database, schema))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/sql/schema", methods=["GET"])
    def sql_get_schema(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sql":
            return _err("Connector is not of type sql", 409)
        database = request.args.get("database")
        schema = request.args.get("schema", "public")
        try:
            from connectors.sql.service import SQLService
            svc = SQLService(locator)
            return jsonify(svc.get_schema(connector_id, database, schema))
        except Exception as exc:
            return _err(str(exc), 502)

    @api_bp.route("/connectors/<connector_id>/sql/describe", methods=["GET"])
    def sql_describe_table(connector_id: str):
        connector, err = _get_connector_or_404(connector_id)
        if err:
            return err
        if connector.type != "sql":
            return _err("Connector is not of type sql", 409)
        table = request.args.get("table")
        if not table:
            return _err("query param 'table' required")
        database = request.args.get("database")
        schema = request.args.get("schema", "public")
        try:
            from connectors.sql.service import SQLService
            svc = SQLService(locator)
            return jsonify(svc.describe_table(connector_id, table, database, schema))
        except Exception as exc:
            return _err(str(exc), 502)
