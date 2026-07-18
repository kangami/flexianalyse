"""Logique métier — Rôles et Permissions."""
from uuid import UUID
from datetime import datetime
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

    def get_org_id(self, role_id: str) -> str | None:
        """Organisation d'un rôle — sert à valider l'appartenance avant mutation."""
        role = self._loc.roles.get_by_id(UUID(role_id))
        return str(role.organization_id) if role else None

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

    def list_all_with_roles(self, org_id: str | None = None) -> list[dict]:
        """List permissions with their roles, optionally scoped to one organisation."""
        role_perms = self._loc.role_permissions.list_all()
        results = []
        for rp in role_perms:
            role = self._loc.roles.get_by_id(rp.role_id)
            if not role:
                continue
            if org_id and str(role.organization_id) != org_id:
                continue
            perm = self._loc.permissions.get_by_id(rp.permission_id)
            if role and perm:
                results.append({
                    "id": str(perm.id),
                    "action": perm.action,
                    "resource": perm.resource,
                    "role_id": str(rp.role_id),
                    "role_name": role.name,
                })
        return results

    def create(self, role_id: str, action: str, resource: str, scope: str = "org") -> dict:
        perm = self._loc.permissions.find_by_action_resource(action, resource)
        if not perm:
            perm = Permission(action=Action(action), resource=Resource(resource), scope=scope)
            perm = self._loc.permissions.create(perm)
        self._loc.role_permissions.link(UUID(role_id), perm.id)
        return perm_to_dict(perm)

    def create_bulk(
        self,
        role_id: str,
        actions: list[str],
        resource: str,
        scope: str = "org",
        valid_from: str | None = None,
        valid_to: str | None = None,
    ) -> dict:
        """Create multiple permissions for a role.
        
        - Checks that action+resource combo doesn't already exist
        - Prevents duplicate role-permission assignments
        - Supports validity date ranges
        - Tracks new vs duplicate assignments
        """
        created = []
        duplicates = []
        role_uuid = UUID(role_id)
        
        for action in actions:
            # Check if permission (action, resource) exists
            perm = self._loc.permissions.find_by_action_resource(action, resource)
            
            if not perm:
                # Create new permission if it doesn't exist
                perm = Permission(
                    action=Action(action),
                    resource=Resource(resource),
                    scope=scope,
                )
                if valid_from:
                    perm.valid_from = datetime.fromisoformat(valid_from)
                if valid_to:
                    perm.valid_to = datetime.fromisoformat(valid_to)
                perm = self._loc.permissions.create(perm)
            
            # Check if this role-permission link already exists
            existing = self._loc.role_permissions.find_link(role_uuid, perm.id)
            if not existing:
                # Only create the link if it doesn't exist
                self._loc.role_permissions.link(role_uuid, perm.id)
                created.append({"action": action, "resource": resource})
            else:
                # This role already has this permission
                duplicates.append({"action": action, "resource": resource})
        
        return {
            "role_id": role_id,
            "created": created,
            "duplicates": duplicates,
            "total_created": len(created),
            "total_duplicates": len(duplicates),
        }

    def delete(self, permission_id: str) -> bool:
        """Soft delete a permission."""
        return self._loc.permissions.soft_delete(UUID(permission_id))
