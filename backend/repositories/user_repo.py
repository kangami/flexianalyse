from typing import Optional, List
from uuid import UUID
from models.user import User, UserSession
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Accès aux données de la table users."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[User]:
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return User(**row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.db.fetch_one(
            "SELECT * FROM users WHERE email = %s AND deleted_at IS NULL", (email,)
        )
        return User(**row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        rows = self.db.fetch_all(
            "SELECT * FROM users WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [User(**r) for r in rows]

    def create(self, entity: User) -> User:
        row = self.db.fetch_one(
            """INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s) RETURNING *""",
            (entity.email, entity.password_hash, entity.full_name)
        )
        return User(**row)

    def update(self, entity: User) -> User:
        row = self.db.fetch_one(
            """UPDATE users SET email = %s, full_name = %s WHERE id = %s AND deleted_at IS NULL RETURNING *""",
            (entity.email, entity.full_name, entity.id)
        )
        return User(**row) if row else None

    def soft_delete(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE users SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM users WHERE id = %s", (id,))
        return result.rowcount > 0


class UserSessionRepository(BaseRepository[UserSession]):
    """Accès aux données de la table user_sessions."""

    def __init__(self, db_connection):
        self.db = db_connection

    def get_by_id(self, id: UUID) -> Optional[UserSession]:
        row = self.db.fetch_one(
            "SELECT * FROM user_sessions WHERE id = %s", (id,)
        )
        return UserSession(**row) if row else None

    def get_by_refresh_token_hash(self, token_hash: str) -> Optional[UserSession]:
        row = self.db.fetch_one(
            "SELECT * FROM user_sessions WHERE refresh_token_hash = %s AND revoked_at IS NULL AND expires_at > now()",
            (token_hash,)
        )
        return UserSession(**row) if row else None

    def list_by_user(self, user_id: UUID) -> List[UserSession]:
        rows = self.db.fetch_all(
            "SELECT * FROM user_sessions WHERE user_id = %s AND revoked_at IS NULL ORDER BY created_at DESC",
            (user_id,)
        )
        return [UserSession(**r) for r in rows]

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserSession]:
        rows = self.db.fetch_all(
            "SELECT * FROM user_sessions ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return [UserSession(**r) for r in rows]

    def create(self, entity: UserSession) -> UserSession:
        row = self.db.fetch_one(
            """INSERT INTO user_sessions (user_id, refresh_token_hash, expires_at, user_agent, ip_address)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (entity.user_id, entity.refresh_token_hash, entity.expires_at, entity.user_agent, entity.ip_address)
        )
        return UserSession(**row)

    def revoke(self, id: UUID) -> bool:
        result = self.db.execute(
            "UPDATE user_sessions SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL", (id,)
        )
        return result.rowcount > 0

    def revoke_all_for_user(self, user_id: UUID) -> int:
        result = self.db.execute(
            "UPDATE user_sessions SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL", (user_id,)
        )
        return result.rowcount

    def update(self, entity: UserSession) -> UserSession:
        raise NotImplementedError("Use revoke() instead")

    def soft_delete(self, id: UUID) -> bool:
        return self.revoke(id)

    def hard_delete(self, id: UUID) -> bool:
        result = self.db.execute("DELETE FROM user_sessions WHERE id = %s", (id,))
        return result.rowcount > 0
