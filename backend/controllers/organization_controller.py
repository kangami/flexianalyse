"""Routes — Organisations."""
from flask import request, jsonify
from services import AuthService, locator, OrganizationService
from services.request_context import current_user, is_member_of, member_org_ids

org_service = OrganizationService(locator)
auth_service = AuthService(locator)


def register(api_bp):
    @api_bp.route("/organizations", methods=["GET"])
    def list_organizations():
        # Scopé aux organisations de l'utilisateur : sans ça, chacun voyait TOUS
        # les tenants, et le front sélectionnait la première org globale — d'où
        # deux comptes distincts qui paraissaient dans la même organisation.
        return jsonify({"data": org_service.list_for_ids(member_org_ids())})

    @api_bp.route("/organizations", methods=["POST"])
    def create_organization():
        data = request.get_json() or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        try:
            created = org_service.create(name)
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        # Le créateur devient owner, sinon l'org n'apparaîtrait pas dans sa liste.
        user = current_user()
        if user:
            auth_service.attach_owner(user.id, created["id"])
        return jsonify(created), 201

    @api_bp.route("/organizations/<org_id>", methods=["PUT"])
    def update_organization(org_id):
        if not is_member_of(org_id):
            return jsonify({"error": "Organisation introuvable"}), 404
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
        if not is_member_of(org_id):
            return jsonify({"error": "Organisation introuvable"}), 404
        ok = org_service.delete(org_id)
        if not ok:
            return jsonify({"error": "Organisation not found"}), 404
        return jsonify({"ok": True})
