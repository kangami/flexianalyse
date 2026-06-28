"""Dropbox Tools for the Dropbox MCP Server.

Uses the official Dropbox Python SDK (``dropbox`` package).
The access token is supplied per-instance (from the incoming Bearer token),
so one DropboxTools object is created per request in server.py.
"""
import logging
from typing import Any

import dropbox
from dropbox.files import (
    FileMetadata,
    FolderMetadata,
    ListFolderResult,
    SearchV2Result,
)
from dropbox.exceptions import ApiError, AuthError

logger = logging.getLogger(__name__)


class DropboxTools:
    """Wrapper around the official Dropbox Python SDK."""

    def __init__(self, access_token: str) -> None:
        self.dbx = dropbox.Dropbox(oauth2_access_token=access_token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_entry(entry) -> dict[str, Any]:
        """Convert a Dropbox metadata entry to a serializable dict."""
        data: dict[str, Any] = {
            "id": getattr(entry, "id", None),
            "name": entry.name,
            "path_lower": entry.path_lower,
            "path_display": entry.path_display,
        }
        if isinstance(entry, FileMetadata):
            data["tag"] = "file"
            data["size"] = entry.size
            data["client_modified"] = entry.client_modified.isoformat() if entry.client_modified else None
            data["server_modified"] = entry.server_modified.isoformat() if entry.server_modified else None
        elif isinstance(entry, FolderMetadata):
            data["tag"] = "folder"
            data["size"] = None
            data["client_modified"] = None
            data["server_modified"] = None
        return data

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def list_folder(
        self, path: str = "", recursive: bool = False, limit: int = 50
    ) -> dict[str, Any]:
        """List the contents of a Dropbox folder.

        Args:
            path: Dropbox path ('' = root, or '/folder/sub').
            recursive: Whether to recurse into sub-folders.
            limit: Maximum number of entries to return.

        Returns:
            Dictionary with entries list.
        """
        try:
            result: ListFolderResult = self.dbx.files_list_folder(
                path, recursive=recursive, limit=min(limit, 2000)
            )
            entries = [self._serialize_entry(e) for e in result.entries]
            return {
                "status": "success",
                "entries": entries,
                "has_more": result.has_more,
                "cursor": result.cursor,
                "count": len(entries),
            }
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def list_folder_continue(self, cursor: str) -> dict[str, Any]:
        """Fetch the next page of a previous list_folder call.

        Args:
            cursor: The cursor returned by list_folder / list_folder_continue.

        Returns:
            Dictionary with the next batch of entries and pagination state.
        """
        try:
            result: ListFolderResult = self.dbx.files_list_folder_continue(cursor)
            entries = [self._serialize_entry(e) for e in result.entries]
            return {
                "status": "success",
                "entries": entries,
                "has_more": result.has_more,
                "cursor": result.cursor,
                "count": len(entries),
            }
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def search_files(
        self, query: str, path: str = "", limit: int = 20
    ) -> dict[str, Any]:
        """Search for files and folders in Dropbox.

        Args:
            query: Search query string.
            path: Restrict search to this path ('' = entire Dropbox).
            limit: Maximum number of results.

        Returns:
            Dictionary with search results.
        """
        try:
            options = dropbox.files.SearchOptions(
                path=path if path else None,
                max_results=min(limit, 100),
                file_status=dropbox.files.FileStatus.active,
                filename_only=False,
            )
            result: SearchV2Result = self.dbx.files_search_v2(
                query=query, options=options
            )
            entries = []
            for match in result.matches:
                metadata = match.metadata.get_metadata()
                entries.append(self._serialize_entry(metadata))
            return {
                "status": "success",
                "query": query,
                "results": entries,
                "count": len(entries),
            }
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def get_metadata(self, path: str) -> dict[str, Any]:
        """Get metadata for a Dropbox file or folder.

        Args:
            path: Dropbox path (must start with '/').

        Returns:
            Dictionary with file/folder metadata.
        """
        try:
            metadata = self.dbx.files_get_metadata(path)
            result = self._serialize_entry(metadata)
            result["status"] = "success"
            return result
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def download_file_text(self, path: str) -> dict[str, Any]:
        """Download a Dropbox file and return its decoded text content.

        Args:
            path: Dropbox path of the file to download.

        Returns:
            Dictionary with text content.
        """
        try:
            metadata, response = self.dbx.files_download(path)
            content = response.content
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="replace")
            return {
                "status": "success",
                "path": path,
                "name": metadata.name,
                "text": text,
                "size": metadata.size,
            }
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def download_file_base64(self, path: str) -> dict[str, Any]:
        """Download a Dropbox file and return its raw bytes as base64.

        Use this for binary files (PDF, DOCX, XLSX, images...) where a text
        decode would corrupt the content. The base64 round-trip is lossless.

        Args:
            path: Dropbox path of the file to download.

        Returns:
            Dictionary with base64-encoded content.
        """
        import base64

        try:
            metadata, response = self.dbx.files_download(path)
            content = response.content
            return {
                "status": "success",
                "path": path,
                "name": metadata.name,
                "content_base64": base64.b64encode(content).decode("ascii"),
                "size": metadata.size,
            }
        except AuthError as exc:
            return {"status": "error", "message": "Authentication failed", "detail": str(exc)}
        except ApiError as exc:
            return {"status": "error", "message": str(exc.error), "detail": str(exc)}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
