"""
Google Drive service with modern authentication and retry handling.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.services.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """
    Google Drive service with Application Default Credentials and retry handling.

    Features:
    - Application Default Credentials (ADC) for authentication
    - Automatic retry with exponential backoff
    - File discovery and metadata retrieval
    - Pagination handling for large folders
    - Caching for improved performance
    - Comprehensive error handling
    """

    def __init__(
        self,
        retry_handler: Optional[RetryHandler] = None,
        scopes: Optional[List[str]] = None,
    ):
        """
        Initialize Google Drive service.

        Args:
            retry_handler: Custom retry handler instance
            scopes: Custom OAuth scopes for authentication
        """
        self.retry_handler = retry_handler or RetryHandler()
        self.scopes = scopes or ["https://www.googleapis.com/auth/drive.readonly"]

        # Initialize Google Drive API client
        self._service = self._create_service()

        # Simple in-memory cache for metadata and folder listings
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._folder_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _create_service(self):
        """
        Create Google Drive API service using Application Default Credentials.

        Returns:
            Google Drive API service instance
        """
        try:
            credentials, project = google.auth.default(scopes=self.scopes)
            service = build("drive", "v3", credentials=credentials)

            logger.info(f"Google Drive service initialized for project: {project}")
            return service

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise

    def list_files_in_folder(
        self, folder_id: str, mime_type: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all files in a folder with pagination handling.

        Args:
            folder_id: The ID of the folder
            mime_type: Optional MIME type filter
            page_size: Number of files per page

        Returns:
            List of file metadata dictionaries

        Raises:
            HttpError: If API request fails
        """
        # Check cache first
        cache_key = f"{folder_id}:{mime_type or 'all'}"
        if cache_key in self._folder_cache:
            logger.debug(f"Returning cached folder listing for {folder_id}")
            return self._folder_cache[cache_key]

        files = []
        page_token = None

        # Build query
        query_parts = [f"'{folder_id}' in parents", "trashed=false"]
        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")
        query = " and ".join(query_parts)

        def _list_operation():
            fields = (
                "nextPageToken, files(id, name, mimeType, size, "
                "modifiedTime, createdTime, parents)"
            )
            return (
                self._service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    pageToken=page_token,
                    fields=fields,
                )
                .execute()
            )

        try:
            while True:
                result = self.retry_handler.execute_with_retry(_list_operation)

                files.extend(result.get("files", []))
                page_token = result.get("nextPageToken")

                if not page_token:
                    break

            logger.info(f"Listed {len(files)} files in folder {folder_id}")

            # Cache the result
            self._folder_cache[cache_key] = files

            return files

        except HttpError as e:
            logger.error(f"Failed to list files in folder {folder_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            raise

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific file.

        Args:
            file_id: The ID of the file

        Returns:
            File metadata dictionary

        Raises:
            HttpError: If API request fails
        """
        # Check cache first
        if file_id in self._metadata_cache:
            logger.debug(f"Returning cached metadata for file {file_id}")
            return self._metadata_cache[file_id]

        def _metadata_operation():
            fields = (
                "id, name, mimeType, size, modifiedTime, createdTime, "
                "parents, properties"
            )
            return (
                self._service.files()
                .get(
                    fileId=file_id,
                    fields=fields,
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_metadata_operation)

            logger.debug(f"Retrieved metadata for file {file_id}")

            # Cache the result
            self._metadata_cache[file_id] = result

            return result

        except HttpError as e:
            logger.error(f"Failed to get metadata for file {file_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting file metadata: {e}")
            raise

    def get_modification_time(self, file_id: str) -> datetime:
        """
        Get the modification time for a specific file.

        Args:
            file_id: The ID of the file

        Returns:
            Modification time as datetime object

        Raises:
            HttpError: If API request fails
            ValueError: If modification time is not available
        """
        metadata = self.get_file_metadata(file_id)
        modified_time_str = metadata.get("modifiedTime")

        if not modified_time_str:
            raise ValueError(f"No modification time available for file {file_id}")

        # Parse RFC 3339 timestamp (e.g., "2025-10-05T10:00:00.000Z")
        # Python's fromisoformat supports this format starting from 3.7
        try:
            # Remove 'Z' suffix and replace with '+00:00' for proper parsing
            if modified_time_str.endswith("Z"):
                modified_time_str = modified_time_str[:-1] + "+00:00"

            modified_time = datetime.fromisoformat(modified_time_str)
            logger.debug(f"Parsed modification time for {file_id}: {modified_time}")

            return modified_time

        except ValueError as e:
            logger.error(
                f"Failed to parse modification time '{modified_time_str}': {e}"
            )
            raise

    def search_files_by_name_pattern(
        self,
        name_pattern: str,
        parent_folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for files by name pattern.

        Args:
            name_pattern: Pattern to search for (supports contains)
            parent_folder_id: Optional parent folder to search within
            mime_type: Optional MIME type filter

        Returns:
            List of matching file metadata dictionaries

        Raises:
            HttpError: If API request fails
        """
        # Build search query
        query_parts = [f"name contains '{name_pattern}'", "trashed=false"]

        if parent_folder_id:
            query_parts.append(f"'{parent_folder_id}' in parents")

        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")

        query = " and ".join(query_parts)

        def _search_operation():
            fields = (
                "files(id, name, mimeType, size, modifiedTime, " "createdTime, parents)"
            )
            return (
                self._service.files()
                .list(
                    q=query,
                    fields=fields,
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_search_operation)
            files = result.get("files", [])

            logger.info(f"Found {len(files)} files matching pattern '{name_pattern}'")
            return files

        except HttpError as e:
            logger.error(
                f"Failed to search for files with pattern '{name_pattern}': {e}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching files: {e}")
            raise

    def get_folder_structure(self, parent_folder_id: str) -> List[Dict[str, Any]]:
        """
        Get all subfolders within a parent folder.

        Args:
            parent_folder_id: The ID of the parent folder

        Returns:
            List of folder metadata dictionaries

        Raises:
            HttpError: If API request fails
        """
        return self.list_files_in_folder(
            parent_folder_id, mime_type="application/vnd.google-apps.folder"
        )

    def get_timesheet_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Get all timesheet files from the specified folder.

        Specialized method for billing system timesheet discovery.

        Args:
            folder_id: The ID of the timesheet folder

        Returns:
            List of timesheet file metadata, sorted by modification time

        Raises:
            HttpError: If API request fails
        """
        try:
            # Get Excel files that contain "Timesheet" in the name
            excel_mime = (
                "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
            )
            timesheet_files = self.search_files_by_name_pattern(
                "Timesheet_",
                parent_folder_id=folder_id,
                mime_type=excel_mime,
            )

            # Sort by modification time (newest first)
            timesheet_files.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)

            logger.info(f"Found {len(timesheet_files)} timesheet files")
            return timesheet_files

        except Exception as e:
            logger.error(f"Failed to get timesheet files: {e}")
            raise

    def get_files_modified_after_date(
        self, folder_id: str, cutoff_date: datetime, mime_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get files modified after a specific date.

        Args:
            folder_id: The ID of the folder
            cutoff_date: Only return files modified after this date
            mime_type: Optional MIME type filter

        Returns:
            List of file metadata dictionaries

        Raises:
            HttpError: If API request fails
        """
        # Format date for Google Drive API
        formatted_date = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S")

        # Build query
        query_parts = [
            f"'{folder_id}' in parents",
            "trashed=false",
            f"modifiedTime > '{formatted_date}'",
        ]

        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")

        query = " and ".join(query_parts)

        def _search_operation():
            fields = (
                "files(id, name, mimeType, size, modifiedTime, " "createdTime, parents)"
            )
            return (
                self._service.files()
                .list(
                    q=query,
                    fields=fields,
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_search_operation)
            files = result.get("files", [])

            logger.info(f"Found {len(files)} files modified after {formatted_date}")
            return files

        except HttpError as e:
            logger.error(f"Failed to get files modified after {formatted_date}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting files by date: {e}")
            raise

    def get_spreadsheet_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Get all spreadsheet files from a folder.

        Args:
            folder_id: The ID of the folder

        Returns:
            List of spreadsheet file metadata

        Raises:
            HttpError: If API request fails
        """
        # Look for both Google Sheets and Excel files
        sheets_mime = "application/vnd.google-apps.spreadsheet"
        google_sheets = self.list_files_in_folder(folder_id, mime_type=sheets_mime)

        excel_mime = (
            "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
        )
        excel_files = self.list_files_in_folder(
            folder_id,
            mime_type=excel_mime,
        )

        all_spreadsheets = google_sheets + excel_files

        logger.info(
            f"Found {len(all_spreadsheets)} spreadsheet files "
            f"({len(google_sheets)} Google Sheets, {len(excel_files)} Excel)"
        )

        return all_spreadsheets

    def clear_cache(self):
        """Clear all cached data."""
        self._metadata_cache.clear()
        self._folder_cache.clear()
        logger.info("Cleared Drive service cache")

    def get_cache_statistics(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "metadata_cache_size": len(self._metadata_cache),
            "folder_cache_size": len(self._folder_cache),
        }

    def preload_folder_metadata(self, folder_id: str):
        """
        Preload metadata for all files in a folder for better performance.

        Args:
            folder_id: The ID of the folder to preload

        Raises:
            HttpError: If API request fails
        """
        try:
            files = self.list_files_in_folder(folder_id)

            # Preload metadata for all files
            for file_info in files:
                if file_info["id"] not in self._metadata_cache:
                    self.get_file_metadata(file_info["id"])

            logger.info(
                f"Preloaded metadata for {len(files)} files in folder {folder_id}"
            )

        except Exception as e:
            logger.error(f"Failed to preload folder metadata: {e}")
            raise
