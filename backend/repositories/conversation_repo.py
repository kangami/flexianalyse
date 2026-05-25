from typing import Optional, List
from uuid import UUID
from models.conversation import Conversation, Message, ToolCall, ToolApproval
from .base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Accès aux données de la table conversations."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Conversation]:
        row = self.db.fetch_one(
            "SELECT * FROM conversations WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Conversation(**row) if row else None

    def list_by_organization(self, organization_id: UUID, limit: int = 50, offset: int = 0) -> List[Conversation]:
        rows = self.db.fetch_all(
            "SELECT * FROM conversations WHERE organization_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (organization_id, limit, offset)
        )
        return [Conversation(**r) for r in rows]

    def list_by_user(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Conversation]:
        rows = self.db.fetch_all(
            "SELECT * FROM conversations WHERE user_id = %s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (user_id, limit, offset)
        )
        return [Conversation(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        rows = self.db.fetch_all(
            "SELECT * FROM conversations WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Conversation(**r) for r in rows]

    def create(self, entity: Conversation) -> Conversation:
        row = self.db.fetch_one(
            """INSERT INTO conversations (organization_id, user_id, title) VALUES (%s, %s, %s) RETURNING *""",
            (entity.organization_id, entity.user_id, entity.title)
        )
        return Conversation(**row)

    def update(self, entity: Conversation) -> Conversation:
        row = self.db.fetch_one(
            """UPDATE conversations SET title = %s, updated_at = now()
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.title, entity.id)
        )
        return Conversation(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE conversations SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM conversations WHERE id = %s", (id,))
        return result.rowcount > 0


class MessageRepository(BaseRepository[Message]):
    """Accès aux données de la table messages."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[Message]:
        row = self.db.fetch_one(
            "SELECT * FROM messages WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return Message(**row) if row else None

    def list_by_conversation(self, conversation_id: UUID) -> List[Message]:
        rows = self.db.fetch_all(
            "SELECT * FROM messages WHERE conversation_id = %s AND deleted_at IS NULL ORDER BY created_at ASC",
            (conversation_id,)
        )
        return [Message(**r) for r in rows]

    def search_fulltext(self, organization_id: UUID, query: str, limit: int = 50) -> List[Message]:
        rows = self.db.fetch_all(
            """SELECT m.* FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.organization_id = %s AND m.deleted_at IS NULL
               AND m.search_vector @@ plainto_tsquery('french', %s)
               ORDER BY ts_rank(m.search_vector, plainto_tsquery('french', %s)) DESC
               LIMIT %s""",
            (organization_id, query, query, limit)
        )
        return [Message(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Message]:
        rows = self.db.fetch_all(
            "SELECT * FROM messages WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [Message(**r) for r in rows]

    def create(self, entity: Message) -> Message:
        row = self.db.fetch_one(
            """INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING *""",
            (entity.conversation_id, entity.role, entity.content)
        )
        return Message(**row)

    def update(self, entity: Message) -> Message:
        row = self.db.fetch_one(
            """UPDATE messages SET content = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.content, entity.id)
        )
        return Message(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE messages SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM messages WHERE id = %s", (id,))
        return result.rowcount > 0


class ToolCallRepository(BaseRepository[ToolCall]):
    """Accès aux données de la table tool_calls."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[ToolCall]:
        row = self.db.fetch_one(
            "SELECT * FROM tool_calls WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return ToolCall(**row) if row else None

    def list_by_message(self, message_id: UUID) -> List[ToolCall]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_calls WHERE message_id = %s AND deleted_at IS NULL ORDER BY created_at ASC",
            (message_id,)
        )
        return [ToolCall(**r) for r in rows]

    def list_by_connector(self, connector_id: UUID, limit: int = 100) -> List[ToolCall]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_calls WHERE connector_id = %s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT %s",
            (connector_id, limit)
        )
        return [ToolCall(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolCall]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_calls WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [ToolCall(**r) for r in rows]

    def create(self, entity: ToolCall) -> ToolCall:
        row = self.db.fetch_one(
            """INSERT INTO tool_calls (message_id, connector_id, tool_name, input, output, status)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (entity.message_id, entity.connector_id, entity.tool_name,
             entity.input, entity.output, entity.status)
        )
        return ToolCall(**row)

    def update_status(self, id: UUID, status: str, output: dict = None) -> Optional[ToolCall]:
        row = self.db.fetch_one(
            """UPDATE tool_calls SET status = %s, output = COALESCE(%s, output)
               WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (status, output, id)
        )
        return ToolCall(**row) if row else None

    def update(self, entity: ToolCall) -> ToolCall:
        return self.update_status(entity.id, entity.status, entity.output)

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE tool_calls SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM tool_calls WHERE id = %s", (id,))
        return result.rowcount > 0


class ToolApprovalRepository(BaseRepository[ToolApproval]):
    """Accès aux données de la table tool_approvals."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[ToolApproval]:
        row = self.db.fetch_one(
            "SELECT * FROM tool_approvals WHERE id = %s", (id,)
        )
        return ToolApproval(**row) if row else None

    def get_by_tool_call(self, tool_call_id: UUID) -> Optional[ToolApproval]:
        row = self.db.fetch_one(
            "SELECT * FROM tool_approvals WHERE tool_call_id = %s ORDER BY created_at DESC LIMIT 1",
            (tool_call_id,)
        )
        return ToolApproval(**row) if row else None

    def list_pending(self, organization_id: UUID) -> List[ToolApproval]:
        rows = self.db.fetch_all(
            """SELECT ta.* FROM tool_approvals ta
               JOIN tool_calls tc ON ta.tool_call_id = tc.id
               JOIN messages m ON tc.message_id = m.id
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.organization_id = %s AND ta.status = 'pending'
               ORDER BY ta.created_at ASC""",
            (organization_id,)
        )
        return [ToolApproval(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolApproval]:
        rows = self.db.fetch_all(
            "SELECT * FROM tool_approvals ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [ToolApproval(**r) for r in rows]

    def create(self, entity: ToolApproval) -> ToolApproval:
        row = self.db.fetch_one(
            """INSERT INTO tool_approvals (tool_call_id, approver_user_id, status, justification)
               VALUES (%s, %s, %s, %s) RETURNING *""",
            (entity.tool_call_id, entity.approver_user_id, entity.status, entity.justification)
        )
        return ToolApproval(**row)

    def approve(self, id: UUID, approver_user_id: UUID, justification: str = None) -> Optional[ToolApproval]:
        row = self.db.fetch_one(
            """UPDATE tool_approvals SET status = 'approved', approver_user_id = %s,
               justification = %s, approved_at = now()
               WHERE id = %s AND status = 'pending' RETURNING *""",
            (approver_user_id, justification, id)
        )
        return ToolApproval(**row) if row else None

    def deny(self, id: UUID, approver_user_id: UUID, justification: str = None) -> Optional[ToolApproval]:
        row = self.db.fetch_one(
            """UPDATE tool_approvals SET status = 'denied', approver_user_id = %s,
               justification = %s, approved_at = now()
               WHERE id = %s AND status = 'pending' RETURNING *""",
            (approver_user_id, justification, id)
        )
        return ToolApproval(**row) if row else None

    def update(self, entity: ToolApproval) -> ToolApproval:
        row = self.db.fetch_one(
            """UPDATE tool_approvals SET status = %s, justification = %s
               WHERE id = %s RETURNING *""",
            (entity.status, entity.justification, entity.id)
        )
        return ToolApproval(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM tool_approvals WHERE id = %s", (id,))
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM tool_approvals WHERE id = %s", (id,))
        return result.rowcount > 0
