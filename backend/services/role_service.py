"""Logique métier — Rôles et Permissions."""
from uuid import UUID
from models.role import Role
from models.permission import Permission
from models.permission import Action, Resource, RolePermission
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
        role = Role(organization_id=UUID(org_id), name=name)
        created = self._loc.roles.create(role)
        return role_to_dict(created)

    def update(self, role_id: str, name: str, org_id: str) -> dict | None:
        role = self._loc.roles.get_by_id(UUID(role_id))
        if not role:
            return None
        role.name = name
        role.organization_id = UUID(org_id)
        updated = self._loc.roles.update(role)
        return role_to_dict(updated)

    def delete(self, role_id: str) -> bool:
        return self._loc.roles.soft_delete(UUID(role_id))


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
        perm = self._loc.permissions.find_by_action_resource(action, resource)
        if not perm:
            perm = Permission(action=Action(action), resource=Resource(resource), scope=scope)
            perm = self._loc.permissions.create(perm)
        self._loc.role_permissions.link(UUID(role_id), perm.id)
        return perm_to_dict(perm)
