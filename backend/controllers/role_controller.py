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

    @api_bp.route("/roles/<role_id>", methods=["PUT"])
    def update_role(role_id):
        data = request.get_json() or {}
        name = data.get("name")
        organization_id = data.get("organization_id")
        if not name or not organization_id:
            return jsonify({"error": "name and organization_id are required"}), 400
        updated = role_service.update(role_id, name, organization_id)
        if not updated:
            return jsonify({"error": "Role not found"}), 404
        return jsonify(updated)

    @api_bp.route("/roles/<role_id>", methods=["DELETE"])
    def delete_role(role_id):
        if role_service.delete(role_id):
            return jsonify({"ok": True})
        return jsonify({"error": "Role not found"}), 404

    @api_bp.route("/permissions", methods=["GET"])
    def list_permissions():
        role_id = request.args.get("role_id")
        if role_id:
            return jsonify({"data": perm_service.list_all(role_id)})
        else:
            # Return all permissions with role information
            return jsonify({"data": perm_service.list_all_with_roles()})

    @api_bp.route("/permissions", methods=["POST"])
    def create_permission():
        data = request.get_json() or {}
        role_id = data.get("role_id")
        actions = data.get("actions", [])
        resource = data.get("resource")
        scope = data.get("scope", "org")
        valid_from = data.get("valid_from")
        valid_to = data.get("valid_to")
        
        if not role_id or not actions or not resource:
            return jsonify({"error": "role_id, actions (array), and resource are required"}), 400
        
        if not isinstance(actions, list) or len(actions) == 0:
            return jsonify({"error": "actions must be a non-empty array"}), 400
        
        result = perm_service.create_bulk(
            role_id=role_id,
            actions=actions,
            resource=resource,
            scope=scope,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        
        # Return 201 if new permissions were created, 200 if all were duplicates
        status_code = 201 if result["total_created"] > 0 else 200
        return jsonify(result), status_code

    @api_bp.route("/permissions/<permission_id>", methods=["DELETE"])
    def delete_permission(permission_id):
        if perm_service.delete(permission_id):
            return jsonify({"ok": True})
        return jsonify({"error": "Permission not found"}), 404
