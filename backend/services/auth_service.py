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

    def attach_owner(self, user_id, org_id) -> None:
        """Rattache un utilisateur comme owner d'une organisation existante.

        Utilisé quand une org est créée via le panneau : sans membership, elle
        disparaîtrait aussitôt de la liste scopée par appartenance. On flushe le
        rôle avant le membership (Membership.role_id nullable → Postgres exige que
        le rôle existe déjà — cf. _create_with_organization).
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        if isinstance(org_id, str):
            org_id = UUID(org_id)
        if self._loc.memberships.get_active_for_user_org(user_id, org_id):
            return
        role = Role(id=uuid4(), organization_id=org_id, name=OWNER_ROLE_NAME, is_system=True)
        db.session.add(role)
        db.session.flush()
        membership = Membership(
            id=uuid4(), user_id=user_id, organization_id=org_id, role_id=role.id, status="active"
        )
        db.session.add(membership)
        db.session.commit()

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

        # 1. Compte déjà connu — par uid ou par email, y compris soft-deleted.
        #    On inclut les supprimés parce que les contraintes d'unicité (email,
        #    firebase_uid) s'appliquent AUSSI aux lignes soft-deleted : sans ça,
        #    un INSERT échouerait sur une ligne que des lectures filtrées ne
        #    voient pas — exactement le blocage observé en production.
        existing = (
            self._loc.users.get_by_firebase_uid(firebase_uid, include_deleted=True)
            or self._loc.users.get_by_email(email, include_deleted=True)
        )
        if existing:
            changed = False
            if existing.deleted_at is not None:
                existing.deleted_at = None
                changed = True
                logger.info("Réactivation d'un compte supprimé : %s", email)
            if existing.firebase_uid != firebase_uid:
                existing.firebase_uid = firebase_uid
                changed = True
            if full_name and not existing.full_name:
                existing.full_name = full_name
                changed = True
            if changed:
                self._loc.users.update(existing)
            self._ensure_default_organization(existing)
            return self.context_for(existing), False

        # 2. Nouveau compte : user + org + rôle owner + membership en une transaction.
        user = self._create_with_organization(firebase_uid, email, full_name)
        return self.context_for(user), True

    def _create_with_organization(self, firebase_uid: str, email: str, full_name: str | None) -> User:
        """Crée l'ensemble en une seule transaction.

        Les repositories committent chacun de leur côté, ce qui laisserait un
        utilisateur sans organisation si une étape échouait. On passe donc par la
        session directement, avec des UUID assignés d'avance pour câbler les FK.

        L'ordre d'insertion est forcé par un flush : Membership.role_id étant
        nullable, SQLAlchemy ne garantit pas d'insérer le rôle avant le membership,
        et Postgres rejette alors la FK (memberships_role_id_fkey). On persiste donc
        org + role + user d'abord (org→role est ordonné car role.organization_id
        est NOT NULL), puis le membership.
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

            try:
                db.session.add_all([org, role, user])
                db.session.flush()          # rôle inséré avant le membership qui le référence
                db.session.add(membership)
                db.session.commit()
                logger.info("Compte provisionné : %s → organisation %s", email, org_name)
                return user
            except IntegrityError as exc:
                db.session.rollback()
                # On logge la contrainte réellement violée : sans ça, l'échec
                # remontait en « Impossible de créer une organisation » opaque.
                logger.warning("Provisionnement %s — tentative %d échouée : %s", email, attempt + 1, exc)
                # Course avec une inscription concurrente sur le même email/uid :
                # la ligne peut avoir été committée entre-temps (soft-deleted inclus).
                clash = (
                    self._loc.users.get_by_firebase_uid(firebase_uid, include_deleted=True)
                    or self._loc.users.get_by_email(email, include_deleted=True)
                )
                if clash:
                    return clash
                # Sinon c'est le nom d'organisation qui a collisionné : la boucle
                # retente avec un suffixe aléatoire.

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
        try:
            db.session.add_all([org, role])
            db.session.flush()              # même contrainte d'ordre que _create_with_organization
            db.session.add(membership)
            db.session.commit()
            logger.info("Organisation par défaut rattachée à %s", user.email)
        except IntegrityError as exc:
            db.session.rollback()
            logger.warning("Échec du rattachement d'une organisation par défaut à %s : %s", user.email, exc)

    def _default_org_name(self, email: str, full_name: str | None) -> str:
        base = (full_name or "").strip() or email.split("@")[0]
        base = re.sub(r"\s+", " ", base).strip()
        return f"{base} {_ORG_SUFFIX}"
