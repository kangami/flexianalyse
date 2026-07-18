import uuid
from datetime import datetime
from config.extensions import db


class User(db.Model):
    """Utilisateur de la plateforme.

    L'identité fait foi côté Firebase : `firebase_uid` est la clé de rattachement,
    et les mots de passe vivent chez Firebase, jamais ici. `password_hash` n'est
    conservé que pour les comptes créés avant cette bascule.
    """
    __tablename__ = 'users'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String, nullable=False, unique=True)
    firebase_uid = db.Column(db.String, nullable=True, unique=True, index=True)
    password_hash = db.Column(db.Text, nullable=True)
    full_name = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class UserSession(db.Model):
    """Session utilisateur (refresh token)."""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    refresh_token_hash = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
