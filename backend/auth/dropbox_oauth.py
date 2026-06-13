"""Dropbox OAuth 2.0 routes for connector authorization."""
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import requests
from flask import Blueprint, jsonify, redirect, request

from models.connector import ConnectorCredentials
from services import locator
from services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)

dropbox_auth_bp = Blueprint("dropbox_auth", __name__, url_prefix="/auth")

_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
_REDIRECT_URI = os.environ.get(
    "DROPBOX_REDIRECT_URI",
    "http://localhost:5000/auth/dropbox/callback",
)
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
_SCOPES = os.environ.get(
    "DROPBOX_SCOPES",
    "files.metadata.read files.content.read account_info.read",
)


def _client_config() -> tuple[str, str]:
    client_id = os.environ.get("DROPBOX_CLIENT_ID")
    client_secret = os.environ.get("DROPBOX_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("DROPBOX_CLIENT_ID and DROPBOX_CLIENT_SECRET must be set")
    return client_id, client_secret


@dropbox_auth_bp.route("/dropbox")
def dropbox_authorize():
    """Redirect user to the Dropbox consent screen."""
    connector_id = request.args.get("connector_id")
    if not connector_id:
        return jsonify({"error": "connector_id required"}), 400

    try:
        client_id, _ = _client_config()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
        "state": connector_id,
        "token_access_type": "offline",
        "scope": _SCOPES,
    }
    prepared = requests.Request("GET", _AUTH_URL, params=params).prepare()
    return redirect(prepared.url)


@dropbox_auth_bp.route("/dropbox/callback")
def dropbox_callback():
    """Exchange a Dropbox authorization code for tokens and store them."""
    connector_id = request.args.get("state")
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        logger.warning("Dropbox OAuth error [%s]: %s", connector_id, error)
        return redirect(f"{_FRONTEND_URL}?connector_error=dropbox&reason={error}")

    if not connector_id or not code:
        return jsonify({"error": "Missing state or code"}), 400

    try:
        client_id, client_secret = _client_config()
        response = requests.post(
            _TOKEN_URL,
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _REDIRECT_URI,
            },
            auth=(client_id, client_secret),
            timeout=20,
        )
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = int(token_data.get("expires_in", 14400))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        encryption = EncryptionService()
        existing = locator.connector_credentials.get_by_connector(UUID(connector_id))
        if existing:
            existing.encrypted_token = encryption.encrypt(access_token)
            existing.refresh_token = encryption.encrypt(refresh_token) if refresh_token else existing.refresh_token
            existing.expires_at = expires_at
            locator.connector_credentials.update(existing)
        else:
            locator.connector_credentials.create(
                ConnectorCredentials(
                    connector_id=UUID(connector_id),
                    encrypted_token=encryption.encrypt(access_token),
                    refresh_token=encryption.encrypt(refresh_token) if refresh_token else None,
                    expires_at=expires_at,
                )
            )

        logger.info("Dropbox credentials stored for connector %s", connector_id)
        return redirect(f"{_FRONTEND_URL}?connector_connected=dropbox&id={connector_id}")
    except Exception as exc:
        logger.error("Dropbox callback error [%s]: %s", connector_id, exc, exc_info=True)
        return redirect(
            f"{_FRONTEND_URL}?connector_error=dropbox&reason=token_exchange_failed"
        )
