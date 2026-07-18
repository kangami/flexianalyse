"""Logique métier — Authentification et provisionnement des comptes.

Fait le pont entre un compte Firebase (source de vérité de l'identité) et les
lignes SQLAlchemy `users` / `organizations` / `roles` / `memberships`.
"""
import logging
import re
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from config.extensions import db
from models.organization import Organization
from models.role import Membership, Role
from models.user import User
from services.serializers import user_to_dict

logger = logging.getLogger(__name__)

# Rôle créé d'office pour le premier membre d'une organisation.
OWNER_ROLE_NAME = "owner"

_ORG_SUFFIX = "workspace"


class AuthService:
    def __init__(self, locator):
        self._loc = locator

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return self._loc.users.get_by_firebase_uid(firebase_uid)

    def context_for(self, user: User) -> dict:
        """Utilisateur + organisations dont il est membre actif."""
        memberships = self._loc.memberships.list_by_user(user.id)
        orgs = []
        for m in memberships:
            if m.status != "active":
                continue
            org = self._loc.organizations.get_by_id(m.organization_id)
            if not org:
                continue
            role = self._loc.roles.get_by_id(m.role_id) if m.role_id else None
            orgs.append({
                "id": str(org.id),
                "name": org.name,
                "role": role.name if role else None,
            })

        payload = user_to_dict(user)
        payload["organizations"] = orgs
        payload["organization_id"] = orgs[0]["id"] if orgs else None
        return payload

    def organization_ids_for(self, user: User) -> set[str]:
        """Organisations dont l'utilisateur est membre actif — base de l'autorisation."""
        return {
            str(m.organization_id)
            for m in self._loc.memberships.list_by_user(user.id)
            if m.status == "active"
        }

    # ------------------------------------------------------------------
    # Provisionnement
    # ------------------------------------------------------------------

    def provision(self, firebase_uid: str, email: str, full_name: str | None = None) -> tuple[dict, bool]:
        """Garantit qu'un compte Firebase a un User + une organisation par défaut.

        Idempotent : rejouer l'appel ne duplique rien. Renvoie (contexte, créé).
        """
        if not firebase_uid or not email:
            raise ValueError("firebase_uid and email are required")

        email = email.strip().lower()

        # 1. Déjà provisionné.
        existing = self._loc.users.get_by_firebase_uid(firebase_uid)
        if existing:
            self._ensure_default_organization(existing)
            return self.context_for(existing), False

        # 2. Compte pré-existant (créé avant Firebase, ou via POST /users) —
        #    on le rattache au lieu de violer la contrainte d'unicité sur l'email.
        by_email = self._loc.users.get_by_email(email)
        if by_email:
            by_email.firebase_uid = firebase_uid
            if full_name and not by_email.full_name:
                by_email.full_name = full_name
            self._loc.users.update(by_email)
            self._ensure_default_organization(by_email)
            return self.context_for(by_email), False

        # 3. Nouveau compte : user + org + rôle owner + membership en une transaction.
        user = self._create_with_organization(firebase_uid, email, full_name)
        return self.context_for(user), True

    def _create_with_organization(self, firebase_uid: str, email: str, full_name: str | None) -> User:
        """Crée l'ensemble en une seule transaction.

        Les repositories committent chacun de leur côté, ce qui laisserait un
        utilisateur sans organisation si une étape échouait. On passe donc par la
        session directement, avec des UUID assignés d'avance pour câbler les FK
        sans flush intermédiaire.
        """
        base_name = self._default_org_name(email, full_name)

        for attempt in range(3):
            org_name = base_name if attempt == 0 else f"{base_name} ({uuid4().hex[:6]})"

            org = Organization(id=uuid4(), name=org_name)
            role = Role(id=uuid4(), organization_id=org.id, name=OWNER_ROLE_NAME, is_system=True)
            user = User(id=uuid4(), email=email, firebase_uid=firebase_uid, full_name=full_name)
            membership = Membership(
                id=uuid4(),
                user_id=user.id,
                organization_id=org.id,
                role_id=role.id,
                status="active",
            )

            db.session.add_all([org, role, user, membership])
            try:
                db.session.commit()
                logger.info("Compte provisionné : %s → organisation %s", email, org_name)
                return user
            except IntegrityError:
                db.session.rollback()
                # Course entre deux inscriptions sur le même nom d'organisation :
                # on retente avec un suffixe. Si c'est l'email/uid qui a doublé,
                # la lecture ci-dessous le résout.
                clash = self._loc.users.get_by_firebase_uid(firebase_uid) or self._loc.users.get_by_email(email)
                if clash:
                    return clash

        raise RuntimeError(f"Impossible de créer une organisation pour {email}")

    def _ensure_default_organization(self, user: User) -> None:
        """Filet de sécurité : un utilisateur sans organisation active en reçoit une.

        Couvre les comptes créés par POST /api/v2/users sans role_id, qui n'ont
        jamais eu de membership.
        """
        active = [m for m in self._loc.memberships.list_by_user(user.id) if m.status == "active"]
        if active:
            return

        base_name = self._default_org_name(user.email, user.full_name)
        org = Organization(id=uuid4(), name=f"{base_name} ({uuid4().hex[:6]})")
        role = Role(id=uuid4(), organization_id=org.id, name=OWNER_ROLE_NAME, is_system=True)
        membership = Membership(
            id=uuid4(),
            user_id=user.id,
            organization_id=org.id,
            role_id=role.id,
            status="active",
        )
        db.session.add_all([org, role, membership])
        try:
            db.session.commit()
            logger.info("Organisation par défaut rattachée à %s", user.email)
        except IntegrityError:
            db.session.rollback()
            logger.warning("Échec du rattachement d'une organisation par défaut à %s", user.email)

    def _default_org_name(self, email: str, full_name: str | None) -> str:
        base = (full_name or "").strip() or email.split("@")[0]
        base = re.sub(r"\s+", " ", base).strip()
        return f"{base} {_ORG_SUFFIX}"
