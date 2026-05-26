import uuid
from datetime import datetime
from config.extensions import db


class Conversation(db.Model):
    """Conversation AI."""
    __tablename__ = 'conversations'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(db.Uuid, db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class Message(db.Model):
    """Message dans une conversation (user / assistant / tool)."""
    __tablename__ = 'messages'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id = db.Column(db.Uuid, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class ToolCall(db.Model):
    """Appel d'outil MCP tracé."""
    __tablename__ = 'tool_calls'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    message_id = db.Column(db.Uuid, db.ForeignKey('messages.id'), nullable=False)
    connector_id = db.Column(db.Uuid, db.ForeignKey('connectors.id'), nullable=True)
    tool_name = db.Column(db.String, nullable=True)
    input = db.Column(db.JSON, default=dict)
    output = db.Column(db.JSON, default=dict)
    status = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class ToolApproval(db.Model):
    """Workflow d'approbation d'un appel d'outil."""
    __tablename__ = 'tool_approvals'

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    tool_call_id = db.Column(db.Uuid, db.ForeignKey('tool_calls.id'), nullable=False)
    approver_user_id = db.Column(db.Uuid, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String, default='pending')
    justification = db.Column(db.Text, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
