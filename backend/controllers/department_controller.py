"""Routes — Départements."""
from flask import request, jsonify
from services import locator, DepartmentService

dept_service = DepartmentService(locator)


def register(api_bp):
    @api_bp.route("/departments", methods=["GET"])
    def list_departments():
        org_id = request.args.get("organization_id")
        return jsonify({"data": dept_service.list_all(org_id)})

    @api_bp.route("/departments", methods=["POST"])
    def create_department():
        data = request.get_json() or {}
        name = data.get("name")
        organization_id = data.get("organization_id")
        if not name or not organization_id:
            return jsonify({"error": "name and organization_id are required"}), 400
        try:
            return jsonify(dept_service.create(name, organization_id)), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 409

    @api_bp.route("/departments/<dept_id>", methods=["PUT"])
    def update_department(dept_id):
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        try:
            updated = dept_service.update(dept_id, name)
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        if not updated:
            return jsonify({"error": "Department not found"}), 404
        return jsonify(updated)

    @api_bp.route("/departments/<dept_id>", methods=["DELETE"])
    def delete_department(dept_id):
        ok = dept_service.delete(dept_id)
        if not ok:
            return jsonify({"error": "Department not found"}), 404
        return jsonify({"ok": True})
