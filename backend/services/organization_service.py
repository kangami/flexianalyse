"""Logique métier — Organisations."""
from uuid import UUID
from models import Organization
from services.serializers import org_to_dict


class OrganizationService:
    def __init__(self, locator):
        self._loc = locator

    def list_all(self) -> list[dict]:
        return [org_to_dict(o) for o in self._loc.organizations.list_all()]

    def create(self, name: str) -> dict:
        if self._loc.organizations.get_by_name(name):
            raise ValueError(f"Organisation '{name}' already exists.")
        org = Organization(id=UUID(int=0), name=name)
        created = self._loc.organizations.create(org)
        return org_to_dict(created)
