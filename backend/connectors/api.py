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

from services import locator
from models.connector import Connector, ConnectorCredentials
import connectors as connector_registry
from services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)
encryption_service = EncryptionService()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connector_to_dict(c: Connector) -> dict:
    return {
        "id": str(c.id),
        "organization_id": str(c.organization_id),
        "type": c.type,
        "name": c.name,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


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
        org_id = request.headers.get("X-Organization-Id")
        if not org_id:
            return _err("X-Organization-Id header required")
        items = locator.connectors.list_by_organization(UUID(org_id))
        return jsonify({"data": [_connector_to_dict(c) for c in items]})

    @api_bp.route("/connectors", methods=["POST"])
    def create_connector():
        data = request.get_json() or {}
        org_id = data.get("organization_id") or request.headers.get("X-Organization-Id")
        connector_type = data.get("type")
        name = data.get("name")
        token = data.get("token")

        if not org_id:
            return _err("organization_id required")
        if connector_type not in connector_registry.CONNECTOR_TYPES:
            return _err(f"type must be one of {connector_registry.CONNECTOR_TYPES}")
        if not name:
            return _err("name required")

        connector = Connector(
            organization_id=UUID(org_id),
            type=connector_type,
            name=name,
            status="active",
        )
        connector = locator.connectors.create(connector)

        if token:
            creds = ConnectorCredentials(
                connector_id=connector.id,
                encrypted_token=encryption_service.encrypt(token),
            )
            locator.connector_credentials.create(creds)

        return jsonify(_connector_to_dict(connector)), 201

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
        locator.connectors.update(connector)
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
