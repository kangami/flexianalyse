"""Logique métier — Organisations."""
from uuid import UUID
from models.organization import Organization
from services.serializers import org_to_dict


class OrganizationService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self) -> list[dict]:
        return [org_to_dict(o) for o in self._loc.organizations.list_all()]

    def create(self, name: str) -> dict:
        if self._loc.organizations.get_by_name(name):
            raise ValueError(f"Organisation '{name}' already exists.")
        org = Organization(name=name)
        created = self._loc.organizations.create(org)
        return org_to_dict(created)

    def update(self, org_id: str, name: str) -> dict | None:
        org = self._loc.organizations.get_by_id(UUID(org_id))
        if not org:
            return None
        existing = self._loc.organizations.get_by_name(name)
        if existing and str(existing.id) != org_id:
            raise ValueError(f"Organisation '{name}' already exists.")
        org.name = name
        updated = self._loc.organizations.update(org)
        return org_to_dict(updated) if updated else None

    def delete(self, org_id: str) -> bool:
        return self._loc.organizations.soft_delete(UUID(org_id))
