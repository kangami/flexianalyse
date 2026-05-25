"""Routes — Organisations."""
from flask import request, jsonify
from services import locator, OrganizationService

org_service = OrganizationService(locator)


def register(api_bp):
    @api_bp.route("/organizations", methods=["GET"])
    def list_organizations():
        return jsonify({"data": org_service.list_all()})

    @api_bp.route("/organizations", methods=["POST"])
    def create_organization():
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        try:
            return jsonify(org_service.create(name)), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 409

    @api_bp.route("/organizations/<org_id>", methods=["PUT"])
    def update_organization(org_id):
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        try:
            updated = org_service.update(org_id, name)
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        if not updated:
            return jsonify({"error": "Organisation not found"}), 404
        return jsonify(updated)

    @api_bp.route("/organizations/<org_id>", methods=["DELETE"])
    def delete_organization(org_id):
        ok = org_service.delete(org_id)
        if not ok:
            return jsonify({"error": "Organisation not found"}), 404
        return jsonify({"ok": True})
