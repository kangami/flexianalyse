import uuid
from datetime import datetime
from config.extensions import db


class Role(db.Model):
    """Rôle au sein d'une organisation (admin, member, external...)."""
    __tablename__ = 'roles'
    __table_args__ = (db.UniqueConstraint('organization_id', 'name', name='uq_role_name_per_org'),)

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class Membership(db.Model):
    """Lien user ↔ organisation avec un rôle (multi-tenant)."""
    __tablename__ = 'memberships'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    role_id = db.Column(db.Uuid, db.ForeignKey('roles.id'), nullable=True)
    status = db.Column(db.String, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
