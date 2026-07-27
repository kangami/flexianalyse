"""Billing routes (Stripe) — registered on api_bp (/api/v2).

  POST /billing/checkout   {plan, interval}  → hosted Checkout URL (auth)
  POST /billing/portal                       → Billing Portal URL (auth)
  GET  /billing/status                       → current plan + subscription (auth)
  POST /billing/webhook                      → Stripe events → sync plan (PUBLIC,
                                               verified by Stripe signature)
"""
import logging
from uuid import UUID

from flask import request, jsonify

from services.request_context import current_organization_id

logger = logging.getLogger(__name__)


def register(api_bp):

    def _org():
        from models.organization import Organization
        org_id = current_organization_id()
        if not org_id:
            return None, (jsonify({"error": "Aucune organisation associée"}), 400)
        org = Organization.query.get(UUID(org_id))
        if not org:
            return None, (jsonify({"error": "Organisation introuvable"}), 404)
        return org, None

    @api_bp.route("/billing/checkout", methods=["POST"])
    def billing_checkout():
        from services.billing import create_checkout_session
        org, err = _org()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        plan = (data.get("plan") or "").strip()
        interval = "year" if data.get("interval") == "year" else "month"
        from flask import g
        email = getattr(getattr(g, "current_user", None), "email", None)
        try:
            url = create_checkout_session(org, plan, interval, email)
            return jsonify({"url": url})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error("Stripe checkout failed: %s", e, exc_info=True)
            return jsonify({"error": "Could not start checkout."}), 502

    @api_bp.route("/billing/portal", methods=["POST"])
    def billing_portal():
        from services.billing import create_portal_session
        org, err = _org()
        if err:
            return err
        try:
            return jsonify({"url": create_portal_session(org)})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error("Stripe portal failed: %s", e, exc_info=True)
            return jsonify({"error": "Could not open the billing portal."}), 502

    @api_bp.route("/billing/status", methods=["GET"])
    def billing_status():
        org, err = _org()
        if err:
            return err
        return jsonify({
            "plan": org.plan,
            "plan_status": org.plan_status,
            "has_subscription": bool(org.stripe_subscription_id),
            "has_customer": bool(org.stripe_customer_id),
        })

    @api_bp.route("/billing/webhook", methods=["POST"])
    def stripe_webhook():
        from services.billing import handle_webhook
        payload = request.get_data()
        sig = request.headers.get("Stripe-Signature", "")
        try:
            typ = handle_webhook(payload, sig)
        except Exception as e:
            logger.warning("Stripe webhook rejected: %s", e)
            return jsonify({"error": "invalid webhook"}), 400
        return jsonify({"received": True, "type": typ})
