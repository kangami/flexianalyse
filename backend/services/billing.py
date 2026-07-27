"""Stripe billing — checkout, customer portal, and the webhook that syncs the
organisation's plan.

Price IDs live in env (one per plan × interval) so the code never hardcodes them.
The webhook is the source of truth: it maps the subscribed price back to a plan and
writes Organization.plan / plan_status. Stripe Tax is enabled on checkout so GST/
HST/VAT are handled by region regardless of the USD prices.

Env:
  STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_PRO_MONTH / _YEAR, STRIPE_PRICE_BUSINESS_MONTH / _YEAR
  FRONTEND_URL  (success/cancel/return redirects)
"""
import os
import logging

logger = logging.getLogger(__name__)

# Plans that are actually purchasable via Stripe (free = default, enterprise = sales).
BILLABLE_PLANS = {"pro", "business"}


def _stripe():
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    return stripe


def _price_map() -> dict:
    return {
        ("pro", "month"): os.getenv("STRIPE_PRICE_PRO_MONTH"),
        ("pro", "year"): os.getenv("STRIPE_PRICE_PRO_YEAR"),
        ("business", "month"): os.getenv("STRIPE_PRICE_BUSINESS_MONTH"),
        ("business", "year"): os.getenv("STRIPE_PRICE_BUSINESS_YEAR"),
    }


def price_for(plan: str, interval: str) -> str | None:
    return _price_map().get((plan, "year" if interval == "year" else "month"))


def plan_for_price(price_id: str) -> str | None:
    for (plan, _interval), pid in _price_map().items():
        if pid and pid == price_id:
            return plan
    return None


def _frontend() -> str:
    return (os.getenv("FRONTEND_URL", "https://www.flexianalyse.com") or "").rstrip("/")


def _ensure_customer(org, email: str | None = None) -> str:
    from config.extensions import db
    if org.stripe_customer_id:
        return org.stripe_customer_id
    cust = _stripe().Customer.create(
        name=org.name, email=email, metadata={"organization_id": str(org.id)},
    )
    org.stripe_customer_id = cust.id
    db.session.commit()
    return cust.id


def create_checkout_session(org, plan: str, interval: str, email: str | None = None) -> str:
    """Hosted Checkout URL for an org to subscribe to a paid plan."""
    if plan not in BILLABLE_PLANS:
        raise ValueError(f"Plan '{plan}' is not purchasable online.")
    price = price_for(plan, interval)
    if not price:
        raise ValueError(f"No Stripe price configured for {plan}/{interval}.")
    stripe = _stripe()
    customer = _ensure_customer(org, email)
    fe = _frontend()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer,
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{fe}/app?billing=success",
        cancel_url=f"{fe}/pricing?billing=cancel",
        client_reference_id=str(org.id),
        subscription_data={"metadata": {"organization_id": str(org.id), "plan": plan}},
        automatic_tax={"enabled": True},          # Stripe Tax: GST/HST/VAT by region
        customer_update={"address": "auto"},
        allow_promotion_codes=True,
    )
    return session.url


def create_portal_session(org) -> str:
    """Stripe Billing Portal URL for the customer to manage / cancel their plan."""
    if not org.stripe_customer_id:
        raise ValueError("This organisation has no billing customer yet.")
    ps = _stripe().billing_portal.Session.create(
        customer=org.stripe_customer_id, return_url=f"{_frontend()}/app",
    )
    return ps.url


def _apply_subscription(org, sub) -> None:
    """Write the org's plan/status from a Stripe subscription object."""
    from config.extensions import db
    try:
        price_id = sub["items"]["data"][0]["price"]["id"]
    except Exception:
        price_id = None
    status = sub.get("status")
    org.stripe_subscription_id = sub.get("id")
    org.plan_status = status
    if status in ("active", "trialing", "past_due"):
        org.plan = plan_for_price(price_id) or org.plan
    elif status in ("canceled", "unpaid", "incomplete_expired"):
        org.plan = "free"
    db.session.commit()
    logger.info("Billing: org %s -> plan=%s status=%s", org.id, org.plan, status)


def _org_for_subscription(sub):
    from uuid import UUID
    from models.organization import Organization
    org_id = (sub.get("metadata") or {}).get("organization_id")
    if org_id:
        try:
            org = Organization.query.get(UUID(org_id))
            if org:
                return org
        except Exception:
            pass
    cust = sub.get("customer")
    if cust:
        return Organization.query.filter_by(stripe_customer_id=cust).first()
    return None


def handle_webhook(payload: bytes, sig_header: str) -> str:
    """Verify a Stripe webhook and sync the org's plan. Returns the event type."""
    from uuid import UUID
    from models.organization import Organization
    stripe = _stripe()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    typ = event["type"]
    obj = event["data"]["object"]

    if typ == "checkout.session.completed":
        org_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("organization_id")
        org = Organization.query.get(UUID(org_id)) if org_id else None
        if org:
            if obj.get("customer"):
                org.stripe_customer_id = obj["customer"]
            sub_id = obj.get("subscription")
            if sub_id:
                _apply_subscription(org, stripe.Subscription.retrieve(sub_id))
    elif typ in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        org = _org_for_subscription(obj)
        if org:
            _apply_subscription(org, obj)

    return typ
