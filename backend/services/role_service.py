"""Logique métier — Rôles et Permissions."""
from uuid import UUID
from models import Role, Permission
from models.permission import Action, Resource
from services.serializers import role_to_dict, perm_to_dict


class RoleService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self, org_id: str | None = None) -> list[dict]:
        if org_id:
            roles = self._loc.roles.list_by_organization(UUID(org_id))
        else:
            roles = self._loc.roles.list_all()
        return [role_to_dict(r) for r in roles]

    def create(self, name: str, org_id: str) -> dict:
        role = Role(id=UUID(int=0), organization_id=UUID(org_id), name=name)
        created = self._loc.roles.create(role)
        return role_to_dict(created)


class PermissionService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self, role_id: str | None = None) -> list[dict]:
        if role_id:
            perms = self._loc.permissions.list_by_role(UUID(role_id))
        else:
            perms = self._loc.permissions.list_all()
        return [perm_to_dict(p) for p in perms]

    def create(self, role_id: str, action: str, resource: str, scope: str = "org") -> dict:
        perm = Permission(id=UUID(int=0), role_id=UUID(role_id), action=Action(action), resource=Resource(resource), scope=scope)
        created = self._loc.permissions.create(perm)
        return perm_to_dict(created)
