"""Plans / tarification — catalogue des paliers + plan courant de l'org.

Le changement de plan n'est PAS exposé ici : sans paiement branché, il se fait en
base (Flask-Admin). Ces routes sont en lecture seule (catalogue + plan courant),
pour la page Plans et le feature-gating côté frontend.
"""
from uuid import UUID

from flask import jsonify

from config.plans import plans_catalog, plan_public
from services.request_context import current_organization_id


def register(api_bp):

    @api_bp.route("/plans", methods=["GET"])
    def list_plans():
        """Catalogue des paliers (nom, prix, features) pour la page Plans."""
        return jsonify({"data": plans_catalog()})

    @api_bp.route("/plan", methods=["GET"])
    def current_plan():
        """Plan courant de l'organisation + features/limites (pour le gating UI)."""
        from models.organization import Organization

        org_id = current_organization_id()
        if not org_id:
            return jsonify({"error": "Aucune organisation associée"}), 400
        org = Organization.query.get(UUID(org_id))
        return jsonify(plan_public(org.plan if org else None))
