"""Logique métier — Départements."""
from uuid import UUID
from models.department import Department
from services.serializers import dept_to_dict


class DepartmentService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self, org_id: str | None = None) -> list[dict]:
        if org_id:
            depts = self._loc.departments.list_by_organization(UUID(org_id))
        else:
            depts = self._loc.departments.list_all()
        return [dept_to_dict(d) for d in depts]

    def get_org_id(self, dept_id: str) -> str | None:
        """Organisation d'un département — validation d'appartenance avant mutation."""
        dept = self._loc.departments.get_by_id(UUID(dept_id))
        return str(dept.organization_id) if dept else None

    def create(self, name: str, org_id: str) -> dict:
        if self._loc.departments.get_by_name_in_org(UUID(org_id), name):
            raise ValueError(f"Department '{name}' already exists in this organisation.")
        dept = Department(organization_id=UUID(org_id), name=name)
        created = self._loc.departments.create(dept)
        return dept_to_dict(created)

    def update(self, dept_id: str, name: str) -> dict | None:
        dept = self._loc.departments.get_by_id(UUID(dept_id))
        if not dept:
            return None
        if self._loc.departments.get_by_name_in_org(dept.organization_id, name, exclude_id=UUID(dept_id)):
            raise ValueError(f"Department '{name}' already exists in this organisation.")
        dept.name = name
        updated = self._loc.departments.update(dept)
        return dept_to_dict(updated) if updated else None

    def delete(self, dept_id: str) -> bool:
        return self._loc.departments.soft_delete(UUID(dept_id))
