"""Routes — Utilisateurs."""
from flask import jsonify, request

from services import AuthService, UserService, locator
from services.request_context import current_organization_id, current_user

user_service = UserService(locator)
auth_service = AuthService(locator)


def register(api_bp):
    @api_bp.route("/users", methods=["POST"])
    def create_user():
        """Crée un utilisateur dans l'organisation courante.

        Ce n'est PAS un endpoint d'inscription — l'inscription passe par Firebase
        puis POST /api/v2/auth/signup. Il sert à ajouter un membre depuis l'admin,
        et exige donc d'être authentifié (cf. before_request de api_bp).
        """
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        role_id = data.get("role_id")
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400
        try:
            return jsonify(user_service.create_with_role(email, password, full_name, role_id)), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 409

    @api_bp.route("/users", methods=["GET"])
    def list_users():
        return jsonify({"data": user_service.list_all()})

    @api_bp.route("/users/me", methods=["GET"])
    def get_current_user():
        """Utilisateur authentifié + ses organisations."""
        payload = auth_service.context_for(current_user())
        payload["current_organization_id"] = current_organization_id()
        return jsonify(payload)
