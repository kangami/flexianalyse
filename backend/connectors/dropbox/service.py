"""Dropbox connector service."""
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import requests

from connectors.base.models import ConnectorConfig
from connectors.dropbox.mcp_client import DropboxMCPClient
from models.connector import Connector
from services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:3004"
_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"


class DropboxService:
    """Business layer for the Dropbox MCP connector."""

    connector_type = "dropbox"

    def __init__(self, locator) -> None:
        self._loc = locator
        self._encryption = get_encryption_service()

    def _decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._encryption.decrypt(value)
        except Exception:
            return value

    def _encrypt(self, value: str | None) -> str | None:
        return self._encryption.encrypt(value) if value else None

    def _refresh_access_token(self, creds) -> str | None:
        refresh_token = self._decrypt(creds.refresh_token)
        if not refresh_token:
            return self._decrypt(creds.encrypted_token)

        client_id = os.environ.get("DROPBOX_CLIENT_ID")
        client_secret = os.environ.get("DROPBOX_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.warning("Dropbox token refresh skipped: client credentials missing")
            return self._decrypt(creds.encrypted_token)

        response = requests.post(
            _TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(client_id, client_secret),
            timeout=20,
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 14400))

        creds.encrypted_token = self._encrypt(access_token)
        creds.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._loc.connector_credentials.update(creds)
        return access_token

    def _build_client(self, connector_id: str) -> tuple[DropboxMCPClient, Connector]:
        connector = self._loc.connectors.get_by_id(UUID(connector_id))
        if not connector:
            raise ValueError(f"Connector '{connector_id}' not found")
        if connector.type != self.connector_type:
            raise TypeError(
                f"Expected connector type '{self.connector_type}', got '{connector.type}'"
            )

        creds = self._loc.connector_credentials.get_by_connector(UUID(connector_id))
        token = None
        if creds:
            now = datetime.now(timezone.utc)
            expires_at = creds.expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at and expires_at <= now + timedelta(minutes=5):
                token = self._refresh_access_token(creds)
            else:
                token = self._decrypt(creds.encrypted_token)

        config = ConnectorConfig(
            server_url=os.environ.get("DROPBOX_MCP_URL", _DEFAULT_SERVER_URL),
            auth_token=token,
        )
        return DropboxMCPClient(config), connector

    def test_connection(self, connector_id: str) -> bool:
        try:
            client, _ = self._build_client(connector_id)
            client.initialize()
            client.get_file_metadata("")
            return True
        except Exception as exc:
            logger.warning("Dropbox connection test failed [%s]: %s", connector_id, exc)
            return False

    def list_tools(self, connector_id: str) -> list[dict]:
        client, _ = self._build_client(connector_id)
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in client.list_tools()
        ]

    def call_tool(self, connector_id: str, tool_name: str, arguments: dict) -> dict:
        client, _ = self._build_client(connector_id)
        return client.call_tool(tool_name, arguments).to_dict()

    def list_resources(self, connector_id: str) -> list[dict]:
        client, _ = self._build_client(connector_id)
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mime_type": r.mime_type,
                "metadata": r.metadata,
            }
            for r in client.list_resources()
        ]

    def read_resource(self, connector_id: str, uri: str) -> str:
        client, _ = self._build_client(connector_id)
        return client.read_resource(uri)

    def list_files(self, connector_id: str, path: str = "", recursive: bool = False, limit: int = 50) -> dict:
        client, _ = self._build_client(connector_id)
        return client.list_files(path, recursive, limit).to_dict()

    def search_files(self, connector_id: str, query: str, path: str = "", limit: int = 20) -> dict:
        client, _ = self._build_client(connector_id)
        return client.search_files(query, path, limit).to_dict()

    def download_file_text(self, connector_id: str, path: str) -> dict:
        client, _ = self._build_client(connector_id)
        return client.download_file_text(path).to_dict()
