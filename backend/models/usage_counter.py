import uuid
from datetime import datetime, timezone
from config.extensions import db


class UsageCounter(db.Model):
    """Per-organisation monthly question counter for the fair-use plan cap.

    One row per (organization, period='YYYY-MM'). Incremented each time a question
    is submitted (natural-language search or direct SQL). Report generation and
    schema syncs do NOT count.
    """
    __tablename__ = 'usage_counters'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False, index=True)
    period = db.Column(db.String, nullable=False)   # 'YYYY-MM' (UTC)
    questions = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'period', name='uq_usage_org_period'),
    )
