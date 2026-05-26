import uuid
from datetime import datetime, timezone
from enum import StrEnum
from config.extensions import db


class AuditAction(StrEnum):
    CREATE = "create"
    READ   = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN  = "login"
    DENIED = "denied"


class AuditLog(db.Model):
    """Log d'audit."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=True)
    user_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String, nullable=True)
    resource = db.Column(db.String, nullable=True)
    tool = db.Column(db.String, nullable=True)
    audit_metadata = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
