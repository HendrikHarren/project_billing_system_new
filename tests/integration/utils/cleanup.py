"""
Cleanup utilities for integration tests.

This module provides utilities to clean up test artifacts created during
integration testing, including:
- Test spreadsheets in Google Drive
- Cache files
- Temporary test data
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.config import BillingSystemConfig
from src.services import GoogleDriveService

logger = logging.getLogger(__name__)


def cleanup_test_spreadsheets(
    config: BillingSystemConfig,
    folder_id: Optional[str] = None,
    prefix: str = "Integration Test",
    older_than_hours: int = 24,
) -> int:
    """
    Clean up old test spreadsheets from Google Drive.

    This function searches for and trashes spreadsheets that:
    1. Have a title starting with the specified prefix
    2. Are older than the specified number of hours
    3. Are located in the specified folder (if provided)

    Args:
        config: Billing system configuration
        folder_id: Optional folder ID to search in (default: monthly invoicing folder)
        prefix: Title prefix to identify test files (default: "Integration Test")
        older_than_hours: Only delete files older than this many hours (default: 24)

    Returns:
        int: Number of files cleaned up

    Example:
        >>> config = get_config()
        >>> count = cleanup_test_spreadsheets(config, older_than_hours=1)
        >>> print(f"Cleaned up {count} test files")
    """
    drive_service = GoogleDriveService(config=config)

    # Use monthly invoicing folder if not specified
    if folder_id is None:
        folder_id = config.monthly_invoicing_folder_id

    # Search for test files
    query = f"name contains '{prefix}' and '{folder_id}' in parents and trashed=false"

    try:
        files = drive_service.list_files_in_folder(
            folder_id=folder_id, query_filter=query
        )
    except Exception as e:
        logger.error(f"Failed to list files for cleanup: {e}")
        return 0

    # Filter by age
    cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
    files_to_delete = []

    for file in files:
        # Parse modified time
        try:
            modified_time = datetime.fromisoformat(
                file.get("modifiedTime", "").replace("Z", "+00:00")
            )
            if modified_time.replace(tzinfo=None) < cutoff_time:
                files_to_delete.append(file)
        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Failed to parse modified time for file {file.get('id')}: {e}"
            )
            continue

    # Delete old test files
    deleted_count = 0
    for file in files_to_delete:
        try:
            drive_service.trash_file(file["id"])
            logger.info(f"Trashed test file: {file.get('name')} ({file['id']})")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to trash file {file['id']}: {e}")

    return deleted_count


def cleanup_file_list(config: BillingSystemConfig, file_ids: List[str]) -> int:
    """
    Clean up a list of files by ID.

    Args:
        config: Billing system configuration
        file_ids: List of Google Drive file IDs to trash

    Returns:
        int: Number of files successfully cleaned up
    """
    drive_service = GoogleDriveService(config=config)
    deleted_count = 0

    for file_id in file_ids:
        try:
            drive_service.trash_file(file_id)
            logger.info(f"Trashed file: {file_id}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to trash file {file_id}: {e}")

    return deleted_count


def verify_file_deleted(config: BillingSystemConfig, file_id: str) -> bool:
    """
    Verify that a file has been successfully deleted/trashed.

    Args:
        config: Billing system configuration
        file_id: Google Drive file ID to check

    Returns:
        bool: True if file is trashed or doesn't exist, False otherwise
    """
    drive_service = GoogleDriveService(config=config)

    try:
        file_metadata = drive_service.get_file_metadata(file_id)
        return file_metadata.get("trashed", False)
    except Exception:
        # File doesn't exist or is inaccessible - consider it deleted
        return True
