"""Logique métier — Utilisateurs."""
from uuid import UUID
import hashlib
from models import User
from services.serializers import user_to_dict


class UserService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self) -> list[dict]:
        return [user_to_dict(u) for u in self._loc.users.list_all()]

    def create(self, email: str, password: str, full_name: str | None = None) -> dict:
        existing = self._loc.users.get_by_email(email)
        if existing:
            raise ValueError("User already exists")
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user = User(id=UUID(int=0), email=email, password_hash=password_hash, full_name=full_name)
        created = self._loc.users.create(user)
        return user_to_dict(created)
