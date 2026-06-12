"""Google Drive OAuth 2.0 routes.

Flow
----
1. Frontend saves the connector (name only) via POST /api/v2/connectors → gets connector_id.
2. Frontend opens  GET /auth/google_drive?connector_id=<id>
3. User authorises on Google consent screen.
4. Google redirects to  GET /auth/google_drive/callback?code=...&state=<connector_id>
5. Backend exchanges code for access + refresh token.
6. Tokens stored in ConnectorCredentials.
7. Browser redirected back to the frontend.

Required env vars
-----------------
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI  (default: http://localhost:5000/auth/google_drive/callback)
FRONTEND_URL         (default: http://localhost:5173)
"""
import logging
import os
from uuid import UUID

from flask import Blueprint, jsonify, redirect, request
from google_auth_oauthlib.flow import Flow

from models.connector import ConnectorCredentials
from services import locator

logger = logging.getLogger(__name__)

gdrive_auth_bp = Blueprint("gdrive_auth", __name__, url_prefix="/auth")

_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/google_drive/callback")
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def _build_flow() -> Flow:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_REDIRECT_URI],
            }
        },
        scopes=_SCOPES,
        redirect_uri=_REDIRECT_URI,
    )


@gdrive_auth_bp.route("/google_drive")
def google_drive_authorize():
    """Redirect user to Google consent screen."""
    connector_id = request.args.get("connector_id")
    if not connector_id:
        return jsonify({"error": "connector_id required"}), 400

    try:
        flow = _build_flow()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=connector_id,
    )
    return redirect(auth_url)


@gdrive_auth_bp.route("/google_drive/callback")
def google_drive_callback():
    """Exchange authorization code for tokens and store them."""
    connector_id = request.args.get("state")
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        logger.warning("Google Drive OAuth error [%s]: %s", connector_id, error)
        return redirect(f"{_FRONTEND_URL}?connector_error=google_drive&reason={error}")

    if not connector_id or not code:
        return jsonify({"error": "Missing state or code"}), 400

    try:
        flow = _build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        existing = locator.connector_credentials.get_by_connector(UUID(connector_id))
        if existing:
            existing.encrypted_token = creds.token
            existing.refresh_token = creds.refresh_token or existing.refresh_token
            locator.connector_credentials.update(existing)
        else:
            new_creds = ConnectorCredentials(
                connector_id=UUID(connector_id),
                encrypted_token=creds.token,
                refresh_token=creds.refresh_token,
                expires_at=creds.expiry,
            )
            locator.connector_credentials.create(new_creds)

        logger.info("Google Drive credentials stored for connector %s", connector_id)
        return redirect(
            f"{_FRONTEND_URL}?connector_connected=google_drive&id={connector_id}"
        )
    except Exception as exc:
        logger.error("Google Drive callback error [%s]: %s", connector_id, exc, exc_info=True)
        return redirect(
            f"{_FRONTEND_URL}?connector_error=google_drive&reason=token_exchange_failed"
        )
