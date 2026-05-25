"""Routes — Stubs (conversations, connectors, audit, rate-limits)."""
from flask import jsonify


def register(api_bp):
    @api_bp.route("/conversations", methods=["GET"])
    def list_conversations():
        return jsonify({"message": "GET /conversations — à implémenter", "data": []})

    @api_bp.route("/conversations", methods=["POST"])
    def create_conversation():
        return jsonify({"message": "POST /conversations — à implémenter"}), 201

    @api_bp.route("/conversations/<conversation_id>/messages", methods=["GET"])
    def list_messages(conversation_id: str):
        return jsonify({"message": f"GET /conversations/{conversation_id}/messages — à implémenter", "data": []})

    @api_bp.route("/conversations/<conversation_id>/messages", methods=["POST"])
    def create_message(conversation_id: str):
        return jsonify({"message": f"POST /conversations/{conversation_id}/messages — à implémenter"}), 201

    @api_bp.route("/connectors", methods=["GET"])
    def list_connectors():
        return jsonify({"message": "GET /connectors — à implémenter", "data": []})

    @api_bp.route("/connectors", methods=["POST"])
    def create_connector():
        return jsonify({"message": "POST /connectors — à implémenter"}), 201

    @api_bp.route("/audit-logs", methods=["GET"])
    def list_audit_logs():
        return jsonify({"message": "GET /audit-logs — à implémenter", "data": []})

    @api_bp.route("/rate-limits", methods=["GET"])
    def list_rate_limits():
        return jsonify({"message": "GET /rate-limits — à implémenter", "data": []})
