import uuid
from datetime import datetime
from config.extensions import db


class Organization(db.Model):
    """Organisation — tenant racine du multi-tenant."""
    __tablename__ = 'organizations'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String, nullable=False, unique=True)
    # Palier de facturation — pilote les limites du catalogue de schéma et du
    # retrieval de tables (voir config/plans.py). server_default pour les lignes
    # existantes lors de la migration.
    plan = db.Column(db.String, nullable=False, default='free', server_default='free')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
