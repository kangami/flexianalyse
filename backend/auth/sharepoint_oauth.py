"""SharePoint / Microsoft Graph OAuth 2.0 routes.

Flow
----
1. Frontend saves the connector (name + tenant_id) → gets connector_id.
2. Frontend opens  GET /auth/sharepoint?connector_id=<id>
3. User authorises on Microsoft login.
4. Microsoft redirects to  GET /auth/sharepoint/callback?code=...&state=<connector_id>
5. Backend exchanges code for access token (MSAL).
6. Token stored in ConnectorCredentials.
7. Browser redirected back to the frontend.

Required env vars
-----------------
MS_CLIENT_ID
MS_CLIENT_SECRET
MS_TENANT_ID     (default: "common" — works for any tenant)
MS_REDIRECT_URI  (default: http://localhost:5000/auth/sharepoint/callback)
FRONTEND_URL     (default: http://localhost:5173)
"""
import logging
import os
from uuid import UUID

import msal
from flask import Blueprint, jsonify, redirect, request

from models.connector import ConnectorCredentials
from services import locator

logger = logging.getLogger(__name__)

sharepoint_auth_bp = Blueprint("sharepoint_auth", __name__, url_prefix="/auth")

_SCOPES = ["https://graph.microsoft.com/Files.ReadWrite.All", "offline_access"]
_REDIRECT_URI = os.environ.get("MS_REDIRECT_URI", "http://localhost:5000/auth/sharepoint/callback")
_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def _build_msal_app(tenant_id: str | None = None) -> msal.ConfidentialClientApplication:
    client_id = os.environ.get("MS_CLIENT_ID")
    client_secret = os.environ.get("MS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("MS_CLIENT_ID and MS_CLIENT_SECRET must be set")

    tid = tenant_id or os.environ.get("MS_TENANT_ID", "common")
    authority = f"https://login.microsoftonline.com/{tid}"
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )


@sharepoint_auth_bp.route("/sharepoint")
def sharepoint_authorize():
    """Redirect user to Microsoft login / consent screen."""
    connector_id = request.args.get("connector_id")
    if not connector_id:
        return jsonify({"error": "connector_id required"}), 400

    try:
        app = _build_msal_app()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    auth_url = app.get_authorization_request_url(
        scopes=_SCOPES,
        state=connector_id,
        redirect_uri=_REDIRECT_URI,
    )
    return redirect(auth_url)


@sharepoint_auth_bp.route("/sharepoint/callback")
def sharepoint_callback():
    """Exchange authorization code for tokens and store them."""
    connector_id = request.args.get("state")
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        desc = request.args.get("error_description", error)
        logger.warning("SharePoint OAuth error [%s]: %s", connector_id, desc)
        return redirect(f"{_FRONTEND_URL}?connector_error=sharepoint&reason={error}")

    if not connector_id or not code:
        return jsonify({"error": "Missing state or code"}), 400

    try:
        app = _build_msal_app()
        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=_SCOPES,
            redirect_uri=_REDIRECT_URI,
        )

        if "error" in result:
            raise RuntimeError(result.get("error_description", result["error"]))

        token = result["access_token"]
        refresh = result.get("refresh_token")

        existing = locator.connector_credentials.get_by_connector(UUID(connector_id))
        if existing:
            existing.encrypted_token = token
            if refresh:
                existing.refresh_token = refresh
            locator.connector_credentials.update(existing)
        else:
            new_creds = ConnectorCredentials(
                connector_id=UUID(connector_id),
                encrypted_token=token,
                refresh_token=refresh,
            )
            locator.connector_credentials.create(new_creds)

        logger.info("SharePoint credentials stored for connector %s", connector_id)
        return redirect(
            f"{_FRONTEND_URL}?connector_connected=sharepoint&id={connector_id}"
        )
    except Exception as exc:
        logger.error("SharePoint callback error [%s]: %s", connector_id, exc, exc_info=True)
        return redirect(
            f"{_FRONTEND_URL}?connector_error=sharepoint&reason=token_exchange_failed"
        )
