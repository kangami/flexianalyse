"""Contexte de la requête authentifiée.

Renseigné par le `before_request` de controllers/__init__.py, lu par les
contrôleurs. Module séparé et sans dépendance : `controllers` importe
`connectors.api`, qui a lui-même besoin de ces helpers — les exposer depuis
`controllers` créerait un cycle d'import.
"""
from typing import Optional

from flask import g


def current_user():
    """Ligne `users` authentifiée, ou None hors requête /api/v2."""
    return getattr(g, "current_user", None)


def current_user_id() -> Optional[str]:
    user = current_user()
    return str(user.id) if user else None


def current_organization_id() -> Optional[str]:
    """Organisation courante, déjà validée contre les memberships."""
    return getattr(g, "current_organization_id", None)


def member_org_ids() -> set[str]:
    """Ensemble des organisations dont l'utilisateur est membre actif."""
    return getattr(g, "member_org_ids", set())


def is_member_of(org_id: Optional[str]) -> bool:
    """Vrai si l'utilisateur authentifié appartient à cette organisation.

    Base de l'isolation multi-tenant : tout endpoint scopé à une organisation
    doit passer par ce contrôle avant de lire ou d'écrire ses données.
    """
    return bool(org_id) and org_id in member_org_ids()


def current_claims() -> Optional[dict]:
    """Claims du token Firebase vérifié."""
    return getattr(g, "firebase_claims", None)
