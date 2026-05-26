import uuid
from datetime import datetime
from enum import StrEnum
from config.extensions import db


class Action(StrEnum):
    READ      = "read"
    CREATE    = "create"
    UPDATE    = "update"
    DELETE    = "delete"
    ASSIGN    = "assign"
    EXECUTE   = "execute"
    MANAGE    = "manage"
    EXPORT    = "export"
    SYNC      = "sync"
    AUTHORIZE = "authorize"


class Resource(StrEnum):
    ORGANIZATIONS = "organizations"
    USERS         = "users"
    MEMBERSHIPS   = "memberships"
    DEPARTMENTS   = "departments"
    TEAMS         = "teams"
    ROLES         = "roles"
    PERMISSIONS   = "permissions"
    CONNECTORS    = "connectors"
    DOCUMENTS     = "documents"
    CASES         = "cases"
    ANALYSES      = "analyses"
    PROMPTS       = "prompts"
    AI_AGENTS     = "ai_agents"
    AUDIT_LOGS    = "audit_logs"
    SETTINGS      = "settings"
    BILLING       = "billing"


class Permission(db.Model):
    """Permission IAM-style (catalogue unique action+resource)."""
    __tablename__ = 'permissions'
    __table_args__ = (db.UniqueConstraint('action', 'resource', name='uq_perm_action_resource'),)

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    action = db.Column(db.String, nullable=False)
    resource = db.Column(db.String, nullable=False)
    scope = db.Column(db.String, default='org')
    allowed = db.Column(db.Boolean, default=True)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_to = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class RolePermission(db.Model):
    """Junction many-to-many entre rôles et permissions."""
    __tablename__ = 'role_permissions'

    role_id = db.Column(db.Uuid, db.ForeignKey('roles.id'), primary_key=True)
    permission_id = db.Column(db.Uuid, db.ForeignKey('permissions.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Policy(db.Model):
    """Policy engine avancé avec conditions JSONB et priorité."""
    __tablename__ = 'policies'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=True)
    name = db.Column(db.String, nullable=True)
    effect = db.Column(db.String, nullable=True)
    condition = db.Column(db.JSON, default=dict)
    priority = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_to = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
