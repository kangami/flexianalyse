from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from config.extensions import db
from models.conversation import Conversation, Message, ToolCall, ToolApproval
from .base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Accès aux données de la table conversations."""

    def get_by_id(self, id: UUID) -> Optional[Conversation]:
        return db.session.scalars(
            select(Conversation).where(Conversation.id == id, Conversation.deleted_at.is_(None))
        ).first()

    def list_by_organization(self, organization_id: UUID, limit: int = 50, offset: int = 0) -> List[Conversation]:
        return list(db.session.scalars(
            select(Conversation)
            .where(Conversation.organization_id == organization_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def list_by_user(self, user_id: UUID, limit: int = 50, offset: int = 0) -> List[Conversation]:
        return list(db.session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        return list(db.session.scalars(
            select(Conversation).where(Conversation.deleted_at.is_(None))
            .order_by(Conversation.updated_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Conversation) -> Conversation:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Conversation) -> Conversation:
        entity.updated_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Conversation).where(Conversation.id == id, Conversation.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Conversation, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class MessageRepository(BaseRepository[Message]):
    """Accès aux données de la table messages."""

    def get_by_id(self, id: UUID) -> Optional[Message]:
        return db.session.scalars(
            select(Message).where(Message.id == id, Message.deleted_at.is_(None))
        ).first()

    def list_by_conversation(self, conversation_id: UUID) -> List[Message]:
        return list(db.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.deleted_at.is_(None))
            .order_by(Message.created_at.asc())
        ).all())

    def search_fulltext(self, organization_id: UUID, query: str, limit: int = 50) -> List[Message]:
        from sqlalchemy import text
        stmt = text(
            """SELECT m.* FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE c.organization_id = :org_id AND m.deleted_at IS NULL
               AND m.search_vector @@ plainto_tsquery('french', :query)
               ORDER BY ts_rank(m.search_vector, plainto_tsquery('french', :query)) DESC
               LIMIT :limit"""
        )
        rows = db.session.execute(stmt, {"org_id": organization_id, "query": query, "limit": limit}).mappings().all()
        return [Message(**dict(r)) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Message]:
        return list(db.session.scalars(
            select(Message).where(Message.deleted_at.is_(None))
            .order_by(Message.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: Message) -> Message:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: Message) -> Message:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(Message).where(Message.id == id, Message.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(Message, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class ToolCallRepository(BaseRepository[ToolCall]):
    """Accès aux données de la table tool_calls."""

    def get_by_id(self, id: UUID) -> Optional[ToolCall]:
        return db.session.scalars(
            select(ToolCall).where(ToolCall.id == id, ToolCall.deleted_at.is_(None))
        ).first()

    def list_by_message(self, message_id: UUID) -> List[ToolCall]:
        return list(db.session.scalars(
            select(ToolCall)
            .where(ToolCall.message_id == message_id, ToolCall.deleted_at.is_(None))
            .order_by(ToolCall.created_at.asc())
        ).all())

    def list_by_connector(self, connector_id: UUID, limit: int = 100) -> List[ToolCall]:
        return list(db.session.scalars(
            select(ToolCall)
            .where(ToolCall.connector_id == connector_id, ToolCall.deleted_at.is_(None))
            .order_by(ToolCall.created_at.desc())
            .limit(limit)
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolCall]:
        return list(db.session.scalars(
            select(ToolCall).where(ToolCall.deleted_at.is_(None))
            .order_by(ToolCall.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: ToolCall) -> ToolCall:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update_status(self, id: UUID, status: str, output: dict = None) -> Optional[ToolCall]:
        entity = db.session.scalars(
            select(ToolCall).where(ToolCall.id == id, ToolCall.deleted_at.is_(None))
        ).first()
        if not entity:
            return None
        entity.status = status
        if output is not None:
            entity.output = output
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: ToolCall) -> ToolCall:
        return self.update_status(entity.id, entity.status, entity.output)

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(ToolCall).where(ToolCall.id == id, ToolCall.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(ToolCall, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class ToolApprovalRepository(BaseRepository[ToolApproval]):
    """Accès aux données de la table tool_approvals."""

    def get_by_id(self, id: UUID) -> Optional[ToolApproval]:
        return db.session.get(ToolApproval, id)

    def get_by_tool_call(self, tool_call_id: UUID) -> Optional[ToolApproval]:
        return db.session.scalars(
            select(ToolApproval)
            .where(ToolApproval.tool_call_id == tool_call_id)
            .order_by(ToolApproval.created_at.desc())
            .limit(1)
        ).first()

    def list_pending(self, organization_id: UUID) -> List[ToolApproval]:
        return list(db.session.scalars(
            select(ToolApproval)
            .join(ToolCall, ToolApproval.tool_call_id == ToolCall.id)
            .join(Message, ToolCall.message_id == Message.id)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.organization_id == organization_id,
                ToolApproval.status == 'pending',
            )
            .order_by(ToolApproval.created_at.asc())
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ToolApproval]:
        return list(db.session.scalars(
            select(ToolApproval)
            .order_by(ToolApproval.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: ToolApproval) -> ToolApproval:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def approve(self, id: UUID, approver_user_id: UUID, justification: str = None) -> Optional[ToolApproval]:
        entity = db.session.scalars(
            select(ToolApproval).where(ToolApproval.id == id, ToolApproval.status == 'pending')
        ).first()
        if not entity:
            return None
        entity.status = 'approved'
        entity.approver_user_id = approver_user_id
        entity.justification = justification
        entity.approved_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def deny(self, id: UUID, approver_user_id: UUID, justification: str = None) -> Optional[ToolApproval]:
        entity = db.session.scalars(
            select(ToolApproval).where(ToolApproval.id == id, ToolApproval.status == 'pending')
        ).first()
        if not entity:
            return None
        entity.status = 'denied'
        entity.approver_user_id = approver_user_id
        entity.justification = justification
        entity.approved_at = datetime.utcnow()
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: ToolApproval) -> ToolApproval:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        return self.hard_delete(id)

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(ToolApproval, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
