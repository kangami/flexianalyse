"""SharePoint Tools for fastMcp"""
from typing import Any, Optional
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
import logging
import io

logger = logging.getLogger(__name__)


class SharePointTools:
    """Tools for interacting with SharePoint Online"""
    
    def __init__(self, site_url: str, client_id: str, client_secret: str):
        """
        Initialize SharePoint tools with credentials
        
        Args:
            site_url: SharePoint site URL (e.g., https://tenant.sharepoint.com/sites/sitename)
            client_id: Azure app registration client ID
            client_secret: Azure app registration client secret
        """
        self.site_url = site_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.ctx = None
        self._connect()
    
    def _connect(self):
        """Establish SharePoint connection"""
        try:
            auth_ctx = AuthenticationContext(url=self.site_url)
            auth_ctx.acquire_token_for_app(self.client_id, self.client_secret)
            self.ctx = ClientContext(self.site_url, auth_ctx)
            # Test connection
            self.ctx.web.get().execute_query()
            logger.info("✓ SharePoint connection established")
        except Exception as e:
            logger.error(f"✗ SharePoint connection failed: {str(e)}")
            raise
    
    def search_files(self, query: str, max_results: int = 50) -> dict[str, Any]:
        """
        Search for files across SharePoint sites
        
        Args:
            query: Search query string
            max_results: Maximum number of results
        
        Returns:
            Dictionary with search results
        """
        try:
            web = self.ctx.web
            web.get().execute_query()
            
            lists = web.lists
            lists.get().execute_query()
            
            results = []
            for sp_list in lists:
                if "Document" not in sp_list.list_template_type:
                    continue
                
                items = sp_list.items.get().execute_query()
                
                for item in items:
                    if query.lower() in str(item).lower():
                        results.append({
                            "name": item.properties.get("Title", "N/A"),
                            "library": sp_list.title,
                            "url": item.get_property("FileRef", "N/A"),
                            "modified": str(item.get_property("Modified", "N/A"))
                        })
                        if len(results) >= max_results:
                            break
                
                if len(results) >= max_results:
                    break
            
            return {
                "status": "success",
                "query": query,
                "results": results[:max_results],
                "count": len(results[:max_results])
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_file(self, file_path: str) -> dict[str, Any]:
        """
        Download/read a specific file by path or ID
        
        Args:
            file_path: SharePoint file path (e.g., /sites/sitename/Shared Documents/filename.pdf)
        
        Returns:
            Dictionary with file content and metadata
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(file_path)
            file.get().execute_query()
            
            content = io.BytesIO()
            file.download(content).execute_query()
            
            return {
                "status": "success",
                "file_path": file_path,
                "name": file.name,
                "size": file.length,
                "modified": str(file.time_last_modified),
                "content_url": f"{self.site_url}/{file_path}",
                "content_available": True
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def upload_file(self, library_name: str, file_path: str, file_content: bytes) -> dict[str, Any]:
        """
        Upload a file to a library
        
        Args:
            library_name: SharePoint document library name
            file_path: Target path in library (e.g., 'folder/file.txt')
            file_content: File content as bytes
        
        Returns:
            Dictionary with upload status
        """
        try:
            library = self.ctx.web.lists.get_by_title(library_name)
            target_url = f"{library_name}/{file_path}"
            
            library.upload_file(file_path, file_content).execute_query()
            
            return {
                "status": "success",
                "message": f"File uploaded to {target_url}",
                "target_path": target_url
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_file(self, file_path: str) -> dict[str, Any]:
        """
        Delete a file from SharePoint
        
        Args:
            file_path: SharePoint file path to delete
        
        Returns:
            Dictionary with delete status
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(file_path)
            file.delete_object().execute_query()
            
            return {
                "status": "success",
                "message": f"File deleted: {file_path}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Move file to another folder/library
        
        Args:
            source_path: Current file path
            destination_path: Target path
        
        Returns:
            Dictionary with move status
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(source_path)
            file.moveto(destination_path, 1).execute_query()  # 1 = overwrite if exists
            
            return {
                "status": "success",
                "message": f"File moved from {source_path} to {destination_path}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """
        Copy file to another location
        
        Args:
            source_path: Current file path
            destination_path: Target path
        
        Returns:
            Dictionary with copy status
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(source_path)
            file.copyto(destination_path, True).execute_query()  # True = overwrite if exists
            
            return {
                "status": "success",
                "message": f"File copied from {source_path} to {destination_path}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_file_versions(self, file_path: str) -> dict[str, Any]:
        """
        List version history of a file
        
        Args:
            file_path: SharePoint file path
        
        Returns:
            Dictionary with version history
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(file_path)
            versions = file.versions.get().execute_query()
            
            return {
                "status": "success",
                "file_path": file_path,
                "versions": [
                    {
                        "version_id": v.id,
                        "created": str(v.created),
                        "created_by": v.created_by.get("Title", "N/A"),
                        "size": v.size,
                        "comment": v.check_in_comment
                    }
                    for v in versions
                ],
                "version_count": len(versions)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def restore_file_version(self, file_path: str, version_id: int) -> dict[str, Any]:
        """
        Restore a previous version of a file
        
        Args:
            file_path: SharePoint file path
            version_id: Version ID to restore
        
        Returns:
            Dictionary with restore status
        """
        try:
            file = self.ctx.web.get_file_by_server_relative_url(file_path)
            version = file.versions.get_by_id(version_id)
            version.restore().execute_query()
            
            return {
                "status": "success",
                "message": f"File {file_path} restored to version {version_id}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
