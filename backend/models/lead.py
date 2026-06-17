import uuid
from datetime import datetime
from config.extensions import db


class Lead(db.Model):
    """Lead capturé via le formulaire Get Started."""
    __tablename__ = 'leads'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    work_email = db.Column(db.String, nullable=False, unique=True)
    company_size = db.Column(db.String, nullable=True)
    country = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=False, default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
