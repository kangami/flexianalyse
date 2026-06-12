"""Google Drive Tools for fastMcp"""
from typing import Any, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# Google Drive scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveTools:
    """Tools for interacting with Google Drive"""
    
    def __init__(self, service_account_json: str):
        """
        Initialize Google Drive tools with service account credentials
        
        Args:
            service_account_json: Path to service account JSON file
        """
        self.service = None
        self._connect(service_account_json)
    
    def _connect(self, service_account_json: str):
        """Establish Google Drive connection"""
        try:
            credentials = Credentials.from_service_account_file(
                service_account_json,
                scopes=SCOPES
            )
            self.service = build("drive", "v3", credentials=credentials)
            logger.info("✓ Google Drive connection established")
        except Exception as e:
            logger.error(f"✗ Google Drive connection failed: {str(e)}")
            raise
    
    def list_documents(self, parent_id: Optional[str] = None, max_results: int = 50) -> dict[str, Any]:
        """
        List all documents in a folder or root Drive
        
        Args:
            parent_id: Folder ID to list contents (None for root)
            max_results: Maximum number of results
        
        Returns:
            Dictionary with document list
        """
        try:
            query = "mimeType != 'application/vnd.google-apps.folder' and trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink, owners)",
                pageSize=max_results,
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get("files", [])
            return {
                "status": "success",
                "documents": [
                    {
                        "id": f["id"],
                        "name": f["name"],
                        "type": f["mimeType"],
                        "size": f.get("size", "N/A"),
                        "created": f.get("createdTime", "N/A"),
                        "modified": f.get("modifiedTime", "N/A"),
                        "link": f.get("webViewLink", "N/A"),
                        "owner": f["owners"][0]["emailAddress"] if f.get("owners") else "N/A"
                    }
                    for f in files
                ],
                "count": len(files)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_folders(self, parent_id: Optional[str] = None, max_results: int = 50) -> dict[str, Any]:
        """
        List all folders in a directory or root Drive
        
        Args:
            parent_id: Parent folder ID (None for root)
            max_results: Maximum number of results
        
        Returns:
            Dictionary with folder list
        """
        try:
            query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, createdTime, modifiedTime, webViewLink, owners)",
                pageSize=max_results,
                orderBy="name"
            ).execute()
            
            folders = results.get("files", [])
            return {
                "status": "success",
                "folders": [
                    {
                        "id": f["id"],
                        "name": f["name"],
                        "created": f.get("createdTime", "N/A"),
                        "modified": f.get("modifiedTime", "N/A"),
                        "link": f.get("webViewLink", "N/A"),
                        "owner": f["owners"][0]["emailAddress"] if f.get("owners") else "N/A"
                    }
                    for f in folders
                ],
                "count": len(folders)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_file_info(self, file_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific file
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            Dictionary with file metadata
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink, owners, description, trashed, parents"
            ).execute()
            
            return {
                "status": "success",
                "file": {
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "type": file.get("mimeType"),
                    "size": file.get("size", "N/A"),
                    "created": file.get("createdTime", "N/A"),
                    "modified": file.get("modifiedTime", "N/A"),
                    "link": file.get("webViewLink", "N/A"),
                    "description": file.get("description", ""),
                    "owner": file["owners"][0]["emailAddress"] if file.get("owners") else "N/A",
                    "parent_ids": file.get("parents", [])
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def search_files(self, query: str, max_results: int = 20) -> dict[str, Any]:
        """
        Search for files by name or content
        
        Args:
            query: Search query string
            max_results: Maximum number of results
        
        Returns:
            Dictionary with search results
        """
        try:
            search_query = f"name contains '{query}' and trashed = false"
            
            results = self.service.files().list(
                q=search_query,
                spaces="drive",
                fields="files(id, name, mimeType, modifiedTime, webViewLink)",
                pageSize=max_results,
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get("files", [])
            return {
                "status": "success",
                "query": query,
                "results": [
                    {
                        "id": f["id"],
                        "name": f["name"],
                        "type": f["mimeType"],
                        "modified": f.get("modifiedTime", "N/A"),
                        "link": f.get("webViewLink", "N/A")
                    }
                    for f in files
                ],
                "count": len(files)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_folder_tree(self, folder_id: Optional[str] = None, max_depth: int = 3, current_depth: int = 0) -> dict[str, Any]:
        """
        Get a tree structure of folders and documents
        
        Args:
            folder_id: Starting folder ID (None for root)
            max_depth: Maximum depth to traverse
            current_depth: Current recursion depth
        
        Returns:
            Dictionary with folder tree structure
        """
        try:
            if current_depth >= max_depth:
                return {"status": "success", "items": []}
            
            query = "trashed = false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()
            
            items = []
            for f in results.get("files", []):
                item = {
                    "id": f["id"],
                    "name": f["name"],
                    "type": f["mimeType"],
                    "is_folder": f["mimeType"] == "application/vnd.google-apps.folder"
                }
                
                # Recursively get subfolders
                if item["is_folder"] and current_depth < max_depth - 1:
                    subtree = self.get_folder_tree(f["id"], max_depth, current_depth + 1)
                    if subtree["status"] == "success":
                        item["children"] = subtree["items"]
                
                items.append(item)
            
            return {"status": "success", "items": items}
        except Exception as e:
            return {"status": "error", "message": str(e)}
