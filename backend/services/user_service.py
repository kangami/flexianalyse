"""Logique métier — Utilisateurs."""
from uuid import UUID
import hashlib
import bcrypt
from models.user import User
from models.role import Membership
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
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        created = self._loc.users.create(user)
        return user_to_dict(created)
    
    def create_with_role(self, email: str, password: str, full_name: str | None = None, role_id: str | None = None) -> dict:
        existing = self._loc.users.get_by_email(email)
        if existing:
            # User exists — assign role/membership if missing
            if role_id:
                role = self._loc.roles.get_by_id(UUID(role_id))
                if not role:
                    raise ValueError("Role not found")
                existing_membership = self._loc.memberships.get_active_for_user_org(existing.id, role.organization_id)
                if not existing_membership:
                    membership = Membership(user_id=existing.id, organization_id=role.organization_id, role_id=UUID(role_id))
                    self._loc.memberships.create(membership)
            return user_to_dict(existing)

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        created = self._loc.users.create(user)

        # Assigner le rôle
        if role_id:
            role = self._loc.roles.get_by_id(UUID(role_id))
            if not role:
                raise ValueError("Role not found")
            existing_membership = self._loc.memberships.get_active_for_user_org(created.id, role.organization_id)
            if not existing_membership:
                membership = Membership(user_id=created.id, organization_id=role.organization_id, role_id=UUID(role_id))
                self._loc.memberships.create(membership)
        return user_to_dict(created)

