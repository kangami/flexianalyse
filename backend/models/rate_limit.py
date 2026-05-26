import uuid
from datetime import datetime
from config.extensions import db


class RateLimit(db.Model):
    """Rate limiting par organisation et type de connecteur."""
    __tablename__ = 'rate_limits'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    connector_type = db.Column(db.String, nullable=False)
    max_requests = db.Column(db.Integer, default=100)
    window_seconds = db.Column(db.Integer, default=60)
    current_count = db.Column(db.Integer, default=0)
    reset_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
