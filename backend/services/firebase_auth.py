"""Vérification des tokens Firebase pour la couche MVC (/api/v2).

`legacy_auth.py` contient déjà une logique équivalente, mais elle n'est pas montée
(main.py:86) et écrit dans un schéma psycopg2 parallèle incompatible avec les
modèles SQLAlchemy. Ce module ne fait que vérifier un token — le mapping vers une
ligne `users` vit dans services/auth_service.py.

L'initialisation est paresseuse : sans elle, une variable Firebase absente ferait
échouer l'import de l'app entière, donc `flask db upgrade`.
"""
import json
import logging
import os
import threading

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialized = False


class FirebaseAuthError(Exception):
    """Token absent, invalide, expiré, ou Firebase non configuré."""


def _ensure_initialized() -> None:
    """Initialise le SDK Admin une seule fois, à la première vérification."""
    global _initialized
    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return

        if firebase_admin._apps:  # déjà initialisé ailleurs (stack legacy)
            _initialized = True
            return

        cred = None
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_json:
            try:
                cred = credentials.Certificate(json.loads(service_account_json))
            except Exception as exc:
                logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON invalide (%s) — fallback fichier", exc)

        if cred is None and service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)

        if cred is None:
            raise FirebaseAuthError(
                "Firebase Admin non configuré : définir FIREBASE_SERVICE_ACCOUNT_JSON "
                "ou FIREBASE_SERVICE_ACCOUNT_PATH."
            )

        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin initialisé (api/v2)")


def verify_token(id_token: str) -> dict:
    """Vérifie un ID token Firebase et renvoie ses claims.

    Lève FirebaseAuthError sur token invalide/expiré ou configuration manquante.
    """
    if not id_token:
        raise FirebaseAuthError("Token manquant")

    _ensure_initialized()

    try:
        return firebase_auth.verify_id_token(id_token)
    except Exception as exc:
        raise FirebaseAuthError(f"Token invalide : {exc}") from exc


def extract_bearer_token(authorization_header: str | None) -> str | None:
    """Extrait le token d'un en-tête `Authorization: Bearer <token>`."""
    if not authorization_header:
        return None
    parts = authorization_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
