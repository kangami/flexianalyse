"""Routes — Utilisateurs."""
from flask import request, jsonify
from services import locator, UserService

user_service = UserService(locator)


def register(api_bp):
    @api_bp.route("/users", methods=["POST"])
    def create_user():
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400
        try:
            return jsonify(user_service.create(email, password, full_name)), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 409

    @api_bp.route("/users", methods=["GET"])
    def list_users():
        return jsonify({"data": user_service.list_all()})

    @api_bp.route("/users/me", methods=["GET"])
    def get_current_user():
        return jsonify({"message": "GET /users/me — à implémenter"})
