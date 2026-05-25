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
