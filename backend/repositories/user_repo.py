from datetime import datetime
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func
from config.extensions import db
from models.user import User, UserSession
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Accès aux données de la table users."""

    def get_by_id(self, id: UUID) -> Optional[User]:
        return db.session.scalars(
            select(User).where(User.id == id, User.deleted_at.is_(None))
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return db.session.scalars(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        ).first()

    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        return db.session.scalars(
            select(User).where(User.firebase_uid == firebase_uid, User.deleted_at.is_(None))
        ).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        return list(db.session.scalars(
            select(User).where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: User) -> User:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def update(self, entity: User) -> User:
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def soft_delete(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(User).where(User.id == id, User.deleted_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.deleted_at = datetime.utcnow()
        db.session.commit()
        return True

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(User, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True


class UserSessionRepository(BaseRepository[UserSession]):
    """Accès aux données de la table user_sessions."""

    def get_by_id(self, id: UUID) -> Optional[UserSession]:
        return db.session.get(UserSession, id)

    def get_by_refresh_token_hash(self, token_hash: str) -> Optional[UserSession]:
        return db.session.scalars(
            select(UserSession)
            .where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > func.now(),
            )
        ).first()

    def list_by_user(self, user_id: UUID) -> List[UserSession]:
        return list(db.session.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.created_at.desc())
        ).all())

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserSession]:
        return list(db.session.scalars(
            select(UserSession)
            .order_by(UserSession.created_at.desc())
            .limit(limit).offset(offset)
        ).all())

    def create(self, entity: UserSession) -> UserSession:
        db.session.add(entity)
        db.session.commit()
        db.session.refresh(entity)
        return entity

    def revoke(self, id: UUID) -> bool:
        entity = db.session.scalars(
            select(UserSession).where(UserSession.id == id, UserSession.revoked_at.is_(None))
        ).first()
        if not entity:
            return False
        entity.revoked_at = datetime.utcnow()
        db.session.commit()
        return True

    def revoke_all_for_user(self, user_id: UUID) -> int:
        sessions = db.session.scalars(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        ).all()
        now = datetime.utcnow()
        for s in sessions:
            s.revoked_at = now
        db.session.commit()
        return len(sessions)

    def update(self, entity: UserSession) -> UserSession:
        raise NotImplementedError("Use revoke() instead")

    def soft_delete(self, id: UUID) -> bool:
        return self.revoke(id)

    def hard_delete(self, id: UUID) -> bool:
        entity = db.session.get(UserSession, id)
        if not entity:
            return False
        db.session.delete(entity)
        db.session.commit()
        return True
