"""Routes — Authentification (provisionnement Firebase → users)."""
import logging

from flask import g, jsonify, request

from services import AuthService, locator
from services.firebase_auth import FirebaseAuthError, extract_bearer_token, verify_token

logger = logging.getLogger(__name__)

auth_service = AuthService(locator)


def register(api_bp):
    @api_bp.route("/auth/signup", methods=["POST"])
    def signup():
        """Crée (ou retrouve) le User + son organisation par défaut.

        Appelée juste après une inscription Firebase, côté client. Le token fait
        foi : ni l'email ni l'uid ne sont lus depuis le corps de la requête, pour
        qu'un appelant ne puisse pas provisionner un compte au nom d'un autre.

        Publique au sens « pas encore de ligne users », mais un token Firebase
        valide reste exigé.
        """
        token = extract_bearer_token(request.headers.get("Authorization"))
        try:
            claims = verify_token(token)
        except FirebaseAuthError as exc:
            logger.warning("Signup — token rejeté : %s", exc)
            return jsonify({"error": "Token invalide ou expiré"}), 401

        firebase_uid = claims.get("uid")
        email = claims.get("email")
        if not email:
            return jsonify({"error": "Le compte Firebase n'expose pas d'email"}), 400

        # full_name du corps seulement s'il n'est pas déjà connu de Firebase :
        # le formulaire d'inscription le collecte avant que le profil soit à jour.
        data = request.get_json(silent=True) or {}
        full_name = claims.get("name") or data.get("full_name")

        try:
            context, created = auth_service.provision(firebase_uid, email, full_name)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(context), 201 if created else 200

    @api_bp.route("/auth/me", methods=["GET"])
    def auth_me():
        """Utilisateur courant + organisations. Exige un compte déjà provisionné."""
        return jsonify(auth_service.context_for(g.current_user))
