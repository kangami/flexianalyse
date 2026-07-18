import logging

from flask import Blueprint, g, jsonify, request
from services import locator
from services.request_context import current_organization_id as _ctx_org_id
from services.request_context import current_user_id as _ctx_user_id
from controllers.organization_controller import register as _register_orgs
from controllers.department_controller import register as _register_depts
from controllers.user_controller import register as _register_users
from controllers.auth_controller import register as _register_auth
from controllers.role_controller import register as _register_roles
from controllers.skeleton_controller import register as _register_skeletons
from controllers.lead_controller import register as _register_leads
from connectors.api import register as _register_connectors

logger = logging.getLogger(__name__)

api_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# Routes joignables sans aucun token.
# `submit_lead` est le formulaire Get Started côté public : il doit rester ouvert.
PUBLIC_ENDPOINTS = {
    "api_v2.submit_lead",
}

# Routes exigeant un token Firebase valide mais PAS encore de ligne `users` :
# c'est précisément l'appel qui la crée.
TOKEN_ONLY_ENDPOINTS = {
    "api_v2.signup",
}


def init_app():
    pass  # DB is now managed by Flask-SQLAlchemy via config/extensions.py


@api_bp.before_request
def _authenticate():
    """Authentifie chaque requête /api/v2 à partir du token Firebase.

    Renseigne `g.current_user`, `g.firebase_claims` et `g.current_organization_id`.
    Avant cette bascule, l'API était intégralement ouverte et se contentait de lire
    des en-têtes X-User-Id / X-Organization-Id falsifiables.
    """
    # Import local : évite un cycle controllers → services.auth_service → models.
    from services.firebase_auth import FirebaseAuthError, extract_bearer_token, verify_token
    from services.auth_service import AuthService

    if request.method == "OPTIONS":
        return None

    endpoint = request.endpoint
    if endpoint in PUBLIC_ENDPOINTS:
        return None

    token = extract_bearer_token(request.headers.get("Authorization"))
    if not token:
        return jsonify({"error": "Authentification requise"}), 401

    try:
        claims = verify_token(token)
    except FirebaseAuthError as exc:
        # Détail journalisé, pas renvoyé : il distingue « token expiré » d'une
        # configuration Firebase absente côté serveur.
        logger.warning("Token /api/v2 rejeté (%s) : %s", endpoint, exc)
        return jsonify({"error": "Token invalide ou expiré"}), 401

    g.firebase_claims = claims

    auth_service = AuthService(locator)
    user = auth_service.get_by_firebase_uid(claims.get("uid"))

    if endpoint in TOKEN_ONLY_ENDPOINTS:
        g.current_user = user
        return None

    if not user:
        # Token valide, mais aucun compte : le client doit passer par /auth/signup.
        return jsonify({"error": "Compte non provisionné", "code": "user_not_provisioned"}), 403

    g.current_user = user

    # L'organisation vient de l'appartenance réelle, jamais d'un en-tête de confiance.
    member_orgs = auth_service.organization_ids_for(user)
    requested_org = request.headers.get("X-Organization-Id")

    if requested_org:
        if requested_org not in member_orgs:
            return jsonify({"error": "Accès refusé à cette organisation"}), 403
        g.current_organization_id = requested_org
    else:
        g.current_organization_id = next(iter(member_orgs), None)

    return None


# Conservés pour compatibilité — l'implémentation vit dans services/request_context.py
# (voir la note de cycle d'import dans ce module).
get_current_user_id = _ctx_user_id
get_current_organization_id = _ctx_org_id


def register_all():
    _register_auth(api_bp)
    _register_orgs(api_bp)
    _register_depts(api_bp)
    _register_users(api_bp)
    _register_roles(api_bp)
    #_register_skeletons(api_bp)
    _register_connectors(api_bp)
    _register_leads(api_bp)
