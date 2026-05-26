import uuid
from datetime import datetime, timezone
from config.extensions import db


class Department(db.Model):
    """Département au sein d'une organisation (IT, Sales, RH...)."""
    __tablename__ = 'departments'
    __table_args__ = (db.UniqueConstraint('organization_id', 'name', name='uq_dept_name_per_org'),)

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(db.DateTime, nullable=True)
