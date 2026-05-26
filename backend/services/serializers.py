"""Conversions dataclass → dict pour la sérialisation JSON."""
from models import Organization, Department, User, Role, Permission
from models.permission import RolePermission


def org_to_dict(o: Organization) -> dict:
    return {"id": str(o.id), "name": o.name, "created_at": o.created_at.isoformat() if o.created_at else None}


def dept_to_dict(d: Department) -> dict:
    return {"id": str(d.id), "organization_id": str(d.organization_id), "name": d.name, "created_at": d.created_at.isoformat() if d.created_at else None}


def user_to_dict(u: User) -> dict:
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name, "created_at": u.created_at.isoformat() if u.created_at else None}


def role_to_dict(r: Role) -> dict:
    return {"id": str(r.id), "organization_id": str(r.organization_id), "name": r.name, "is_system": r.is_system, "created_at": r.created_at.isoformat() if r.created_at else None}


def perm_to_dict(p: Permission) -> dict:
    return {"id": str(p.id), "action": p.action, "resource": p.resource, "scope": p.scope, "allowed": p.allowed, "created_at": p.created_at.isoformat() if p.created_at else None}


def role_perm_to_dict(rp: RolePermission) -> dict:
    return {"role_id": str(rp.role_id), "permission_id": str(rp.permission_id), "created_at": rp.created_at.isoformat() if rp.created_at else None}
