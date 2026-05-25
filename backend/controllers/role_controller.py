"""Routes — Rôles et Permissions."""
from flask import request, jsonify
from services import locator, RoleService, PermissionService

role_service = RoleService(locator)
perm_service = PermissionService(locator)


def register(api_bp):
    @api_bp.route("/roles", methods=["GET"])
    def list_roles():
        org_id = request.args.get("organization_id")
        return jsonify({"data": role_service.list_all(org_id)})

    @api_bp.route("/roles", methods=["POST"])
    def create_role():
        data = request.get_json() or {}
        name = data.get("name")
        organization_id = data.get("organization_id")
        if not name or not organization_id:
            return jsonify({"error": "name and organization_id are required"}), 400
        return jsonify(role_service.create(name, organization_id)), 201

    @api_bp.route("/permissions", methods=["GET"])
    def list_permissions():
        role_id = request.args.get("role_id")
        return jsonify({"data": perm_service.list_all(role_id)})

    @api_bp.route("/permissions", methods=["POST"])
    def create_permission():
        data = request.get_json() or {}
        role_id = data.get("role_id")
        action = data.get("action")
        resource = data.get("resource")
        scope = data.get("scope", "org")
        if not role_id or not action or not resource:
            return jsonify({"error": "role_id, action, and resource are required"}), 400
        return jsonify(perm_service.create(role_id, action, resource, scope)), 201
