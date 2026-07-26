"""Fair-use metering — monthly question cap per organisation.

A "question" = one natural-language search or one direct SQL run submitted by the
user. Report generation and schema syncs do NOT count. The cap comes from the
org's plan (`monthly_questions`); `None` = unlimited (enterprise).
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)


def current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _limit_for(org_id: str):
    from models.organization import Organization
    from config.plans import plan_limits
    org = Organization.query.get(UUID(org_id)) if org_id else None
    return plan_limits(org.plan if org else None).get("monthly_questions")


def get_usage(org_id: str) -> dict:
    """Current-period usage for display: {used, limit, period}."""
    from models.usage_counter import UsageCounter
    limit = _limit_for(org_id)
    period = current_period()
    row = UsageCounter.query.filter_by(organization_id=UUID(org_id), period=period).first()
    return {"used": (row.questions if row else 0), "limit": limit, "period": period}


def check_and_increment(org_id: str) -> tuple[bool, int, int | None]:
    """Reserve one question for this org. Returns (allowed, used, limit).

    Increments the counter when allowed. Never raises — on any error it fails OPEN
    (allows the question) so metering can't take the product down.
    """
    from config.extensions import db
    from models.usage_counter import UsageCounter
    try:
        limit = _limit_for(org_id)
        period = current_period()
        row = UsageCounter.query.filter_by(organization_id=UUID(org_id), period=period).first()
        used = row.questions if row else 0
        if limit is not None and used >= limit:
            return False, used, limit
        if not row:
            row = UsageCounter(organization_id=UUID(org_id), period=period, questions=0)
            db.session.add(row)
        row.questions = (row.questions or 0) + 1
        row.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return True, row.questions, limit
    except Exception as e:
        logger.warning("usage metering failed for org %s (allowing): %s", org_id, e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return True, 0, None
