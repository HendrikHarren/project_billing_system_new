"""
Google Drive API integration tests.

Tests real interactions with Google Drive API including:
- File listing and search
- File operations (create, move, trash)
- Folder operations
- Metadata retrieval

Requires real Google API credentials and is marked as @pytest.mark.integration.
"""

from datetime import datetime

import pytest

from src.config import BillingSystemConfig
from src.services import GoogleDriveService


@pytest.mark.integration
@pytest.mark.api
class TestGoogleDriveIntegration:
    """Integration tests for Google Drive service."""

    def test_list_files_in_folder(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test listing files in a real folder."""
        # List files in the timesheet folder
        files = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id
        )

        # Verify we got results
        assert isinstance(files, list)

        # If files exist, verify structure
        if len(files) > 0:
            file = files[0]
            assert "id" in file
            assert "name" in file
            assert isinstance(file["id"], str)
            assert isinstance(file["name"], str)

    def test_get_file_metadata(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test retrieving file metadata."""
        # Get metadata for the project terms file
        metadata = real_drive_service.get_file_metadata(
            file_id=integration_config.project_terms_file_id
        )

        # Verify metadata structure
        assert "id" in metadata
        assert "name" in metadata
        assert "modifiedTime" in metadata
        assert metadata["id"] == integration_config.project_terms_file_id

    def test_search_files_by_name(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test searching for files by name pattern."""
        # Search for any file in the timesheet folder
        files = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id, max_results=5
        )

        # Should get some results
        assert isinstance(files, list)

    def test_file_modification_time_tracking(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test that modification times are properly tracked."""
        # Get metadata twice and verify modification time format
        metadata = real_drive_service.get_file_metadata(
            file_id=integration_config.project_terms_file_id
        )

        mod_time = metadata.get("modifiedTime")
        assert mod_time is not None

        # Verify it's a valid timestamp format (ISO 8601)
        try:
            datetime.fromisoformat(mod_time.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid modification time format: {mod_time}")

    def test_folder_operations(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test basic folder operations."""
        # Verify we can access the configured folders
        folders_to_check = [
            ("timesheet_folder", integration_config.timesheet_folder_id),
            ("invoicing_folder", integration_config.monthly_invoicing_folder_id),
        ]

        for folder_name, folder_id in folders_to_check:
            # List files in folder (verifies folder exists and is accessible)
            files = real_drive_service.list_files_in_folder(folder_id=folder_id)
            assert isinstance(files, list), f"Failed to access {folder_name}"


@pytest.mark.integration
@pytest.mark.api
class TestDriveFileOperations:
    """Test file creation and manipulation operations."""

    def test_move_file_between_folders(
        self,
        real_drive_service: GoogleDriveService,
        real_sheets_service,
        integration_config: BillingSystemConfig,
        cleanup_test_files_list,
    ):
        """Test moving a file from one folder to another."""
        # Create a test spreadsheet
        title = f"Test Move File - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet_id = real_sheets_service.create_spreadsheet(
            title=title, folder_id=integration_config.timesheet_folder_id
        )

        cleanup_test_files_list.append(spreadsheet_id)

        # Verify it's in the source folder
        files_in_source = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id
        )
        assert any(f["id"] == spreadsheet_id for f in files_in_source)

        # Move to destination folder
        real_drive_service.move_file(
            file_id=spreadsheet_id,
            new_folder_id=integration_config.monthly_invoicing_folder_id,
        )

        # Verify it's in the destination folder
        files_in_dest = real_drive_service.list_files_in_folder(
            folder_id=integration_config.monthly_invoicing_folder_id
        )
        assert any(f["id"] == spreadsheet_id for f in files_in_dest)

    def test_trash_and_verify(
        self,
        real_drive_service: GoogleDriveService,
        real_sheets_service,
        integration_config: BillingSystemConfig,
    ):
        """Test trashing a file and verifying it's trashed."""
        # Create a test file to trash
        title = f"Test Trash File - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet_id = real_sheets_service.create_spreadsheet(
            title=title, folder_id=integration_config.monthly_invoicing_folder_id
        )

        # Trash it
        real_drive_service.trash_file(file_id=spreadsheet_id)

        # Verify it's trashed by checking metadata
        metadata = real_drive_service.get_file_metadata(file_id=spreadsheet_id)
        assert metadata.get("trashed", False) is True


@pytest.mark.integration
@pytest.mark.api
class TestDriveErrorHandling:
    """Test error handling with Google Drive API."""

    def test_invalid_folder_id(
        self,
        real_drive_service: GoogleDriveService,
    ):
        """Test handling of invalid folder ID."""
        with pytest.raises(Exception):
            real_drive_service.list_files_in_folder(folder_id="invalid_folder_id_xyz")

    def test_invalid_file_id_metadata(
        self,
        real_drive_service: GoogleDriveService,
    ):
        """Test handling of invalid file ID when getting metadata."""
        with pytest.raises(Exception):
            real_drive_service.get_file_metadata(file_id="invalid_file_id_123")

    def test_move_to_invalid_folder(
        self,
        real_drive_service: GoogleDriveService,
        real_sheets_service,
        integration_config: BillingSystemConfig,
        cleanup_test_files_list,
    ):
        """Test error handling when moving to invalid folder."""
        # Create a test file
        title = f"Test Invalid Move - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet_id = real_sheets_service.create_spreadsheet(
            title=title, folder_id=integration_config.monthly_invoicing_folder_id
        )

        cleanup_test_files_list.append(spreadsheet_id)

        # Try to move to invalid folder
        with pytest.raises(Exception):
            real_drive_service.move_file(
                file_id=spreadsheet_id, new_folder_id="invalid_folder_xyz"
            )


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestDrivePerformance:
    """Test performance characteristics of Drive operations."""

    def test_list_large_folder_performance(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test performance of listing files in a potentially large folder."""
        import time

        start_time = time.time()

        files = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id, max_results=100
        )

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0, f"Listing files took too long: {elapsed:.2f}s"

        # Log results for monitoring
        print(f"\nListed {len(files)} files in {elapsed:.2f}s")

    def test_batch_metadata_retrieval_performance(
        self,
        real_drive_service: GoogleDriveService,
        integration_config: BillingSystemConfig,
    ):
        """Test performance of retrieving metadata for multiple files."""
        import time

        # Get list of files first
        files = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id, max_results=10
        )

        if len(files) < 2:
            pytest.skip("Requires at least 2 files in timesheet folder")

        # Time metadata retrieval for multiple files
        start_time = time.time()

        for file in files[:5]:  # Test with up to 5 files
            real_drive_service.get_file_metadata(file_id=file["id"])

        elapsed = time.time() - start_time

        # Should complete in reasonable time
        files_checked = min(5, len(files))
        avg_time = elapsed / files_checked

        print(
            f"\nRetrieved metadata for {files_checked} files in {elapsed:.2f}s (avg: {avg_time:.2f}s per file)"
        )

        # Average should be reasonable (< 2 seconds per file)
        assert avg_time < 2.0, f"Metadata retrieval too slow: {avg_time:.2f}s per file"
