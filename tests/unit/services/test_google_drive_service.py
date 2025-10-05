"""
Unit tests for Google Drive service.
"""

from unittest.mock import Mock, patch

import pytest
from googleapiclient.errors import HttpError

from src.services.google_drive_service import GoogleDriveService
from src.services.retry_handler import RetryHandler


class TestGoogleDriveService:
    """Test cases for GoogleDriveService."""

    @pytest.fixture
    def mock_drive_client(self):
        """Mock Google Drive API client."""
        mock_client = Mock()
        mock_files = Mock()

        mock_client.files.return_value = mock_files

        return mock_client

    @pytest.fixture
    def mock_retry_handler(self):
        """Mock retry handler."""
        mock_handler = Mock(spec=RetryHandler)
        mock_handler.execute_with_retry.side_effect = (
            lambda func, *args, **kwargs: func(*args, **kwargs)
        )
        return mock_handler

    @pytest.fixture
    def drive_service(self, mock_drive_client, mock_retry_handler):
        """GoogleDriveService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_drive_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_credentials = Mock()
        mock_auth.return_value = (mock_credentials, "test-project")
        mock_build.return_value = mock_drive_client

        service = GoogleDriveService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_service_initialization(self, mock_retry_handler):
        """Test service initializes with proper authentication."""
        with patch("src.services.google_drive_service.build") as mock_build:
            with patch("google.auth.default") as mock_auth:
                mock_credentials = Mock()
                mock_auth.return_value = (mock_credentials, "test-project")

                service = GoogleDriveService(retry_handler=mock_retry_handler)
                assert service is not None

                mock_auth.assert_called_once_with(
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )
                mock_build.assert_called_once_with(
                    "drive", "v3", credentials=mock_credentials
                )

    def test_list_files_in_folder_success(self, drive_service, mock_drive_client):
        """Test successful listing of files in a folder."""
        mock_response = {
            "files": [
                {
                    "id": "file1",
                    "name": "Timesheet_2024_01.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
                    "modifiedTime": "2024-01-15T10:30:00Z",
                },
                {
                    "id": "file2",
                    "name": "Timesheet_2024_02.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
                    "modifiedTime": "2024-02-15T10:30:00Z",
                },
            ],
            "nextPageToken": None,
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.list_files_in_folder("test-folder-id")

        assert len(result) == 2
        assert result[0]["name"] == "Timesheet_2024_01.xlsx"
        assert result[1]["name"] == "Timesheet_2024_02.xlsx"

    def test_list_files_with_pagination(self, drive_service, mock_drive_client):
        """Test listing files with pagination handling."""
        # First page
        mock_response_1 = {
            "files": [{"id": "file1", "name": "File1.xlsx"}],
            "nextPageToken": "token123",
        }
        # Second page
        mock_response_2 = {
            "files": [{"id": "file2", "name": "File2.xlsx"}],
            "nextPageToken": None,
        }

        mock_list = mock_drive_client.files().list
        mock_list().execute.side_effect = [mock_response_1, mock_response_2]

        result = drive_service.list_files_in_folder("test-folder-id")

        assert len(result) == 2
        # Should make exactly 2 calls for pagination
        assert mock_list().execute.call_count == 2

    def test_list_files_with_filter(self, drive_service, mock_drive_client):
        """Test listing files with MIME type filter."""
        mock_response = {
            "files": [
                {
                    "id": "file1",
                    "name": "Timesheet.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
                }
            ]
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.list_files_in_folder(
            "test-folder-id",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
        )
        assert result is not None

        # Verify filter was applied in query
        call_args = mock_drive_client.files().list.call_args
        query = call_args[1]["q"]
        assert "mimeType=" in query

    def test_get_file_metadata_success(self, drive_service, mock_drive_client):
        """Test successful retrieval of file metadata."""
        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
            "size": "1024",
            "modifiedTime": "2024-01-15T10:30:00Z",
            "createdTime": "2024-01-01T09:00:00Z",
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        result = drive_service.get_file_metadata("file123")

        assert result["name"] == "Test_File.xlsx"
        assert result["size"] == "1024"

    def test_search_files_by_name_pattern(self, drive_service, mock_drive_client):
        """Test searching files by name pattern."""
        mock_response = {
            "files": [
                {"id": "file1", "name": "Timesheet_2024_01.xlsx"},
                {"id": "file2", "name": "Timesheet_2024_02.xlsx"},
            ]
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.search_files_by_name_pattern("Timesheet_2024_*.xlsx")

        assert len(result) == 2
        call_args = mock_drive_client.files().list.call_args
        query = call_args[1]["q"]
        assert "name contains" in query

    def test_get_folder_structure(self, drive_service, mock_drive_client):
        """Test retrieving folder structure."""
        mock_response = {
            "files": [
                {
                    "id": "folder1",
                    "name": "Timesheets",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "folder2",
                    "name": "Archives",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ]
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.get_folder_structure("parent-folder-id")

        assert len(result) == 2
        assert all(
            item["mimeType"] == "application/vnd.google-apps.folder" for item in result
        )

    def test_list_files_with_retry_on_rate_limit(
        self, drive_service, mock_retry_handler, mock_drive_client
    ):
        """Test file listing with retry on rate limit."""
        # Configure mock response
        mock_response = {"files": [], "nextPageToken": None}
        mock_drive_client.files().list().execute.return_value = mock_response

        mock_retry_handler.execute_with_retry.side_effect = lambda func: func()

        drive_service.list_files_in_folder("test-folder-id")

        mock_retry_handler.execute_with_retry.assert_called_once()

    def test_api_error_handling(self, drive_service, mock_drive_client):
        """Test handling of API errors."""
        mock_drive_client.files().list().execute.side_effect = HttpError(
            resp=Mock(status=404), content=b"Not Found"
        )

        with pytest.raises(HttpError):
            drive_service.list_files_in_folder("nonexistent-folder")

    def test_empty_folder_handling(self, drive_service, mock_drive_client):
        """Test handling of empty folders."""
        mock_response = {"files": []}
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.list_files_in_folder("empty-folder-id")

        assert result == []

    def test_get_timesheet_files(self, drive_service, mock_drive_client):
        """Test specialized method for getting timesheet files."""
        mock_response = {
            "files": [
                {
                    "id": "ts1",
                    "name": "Timesheet_John_2024_01.xlsx",
                    "modifiedTime": "2024-01-15T10:30:00Z",
                },
                {
                    "id": "ts2",
                    "name": "Timesheet_Jane_2024_01.xlsx",
                    "modifiedTime": "2024-01-16T10:30:00Z",
                },
            ]
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        result = drive_service.get_timesheet_files("timesheet-folder-id")

        assert len(result) == 2
        assert all("Timesheet_" in file["name"] for file in result)

    def test_get_files_modified_after_date(self, drive_service, mock_drive_client):
        """Test filtering files by modification date."""
        mock_response = {
            "files": [
                {
                    "id": "file1",
                    "name": "Recent_File.xlsx",
                    "modifiedTime": "2024-01-15T10:30:00Z",
                }
            ]
        }
        mock_drive_client.files().list().execute.return_value = mock_response

        from datetime import datetime

        cutoff_date = datetime(2024, 1, 1)

        result = drive_service.get_files_modified_after_date("folder-id", cutoff_date)

        assert len(result) == 1
        call_args = mock_drive_client.files().list.call_args
        query = call_args[1]["q"]
        assert "modifiedTime >" in query


class TestGoogleDriveServiceIntegration:
    """Integration tests for GoogleDriveService."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test requires real Google API credentials")
    def test_real_api_connection(self, test_config):
        """Test connection to real Google Drive API."""
        retry_handler = RetryHandler()
        service = GoogleDriveService(retry_handler=retry_handler)

        # Test listing files in timesheet folder
        files = service.list_files_in_folder(test_config.timesheet_folder_id)

        assert isinstance(files, list)
        assert len(files) > 0

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test requires real Google API credentials")
    def test_timesheet_file_discovery(self, test_config):
        """Test discovery of timesheet files."""
        retry_handler = RetryHandler()
        service = GoogleDriveService(retry_handler=retry_handler)

        timesheet_files = service.get_timesheet_files(test_config.timesheet_folder_id)

        # Should find timesheet files
        assert len(timesheet_files) > 0
        assert all(".xlsx" in file["name"] for file in timesheet_files)


class TestGoogleDriveServiceErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_drive_client(self):
        """Mock Google Drive API client."""
        mock_client = Mock()
        mock_files = Mock()

        mock_client.files.return_value = mock_files

        return mock_client

    @pytest.fixture
    def mock_retry_handler(self):
        """Mock retry handler."""
        mock_handler = Mock(spec=RetryHandler)
        mock_handler.execute_with_retry.side_effect = (
            lambda func, *args, **kwargs: func(*args, **kwargs)
        )
        return mock_handler

    @pytest.fixture
    def drive_service(self, mock_drive_client, mock_retry_handler):
        """GoogleDriveService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_drive_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_credentials = Mock()
        mock_auth.return_value = (mock_credentials, "test-project")
        mock_build.return_value = mock_drive_client

        service = GoogleDriveService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_folder_not_found_handling(self, drive_service, mock_drive_client):
        """Test handling of folder not found errors."""
        not_found_error = HttpError(
            resp=Mock(status=404),
            content=b'{"error": {"code": 404, "message": "File not found"}}',
        )

        mock_drive_client.files().list().execute.side_effect = not_found_error

        with pytest.raises(HttpError):
            drive_service.list_files_in_folder("nonexistent-folder")

    def test_permission_denied_handling(self, drive_service, mock_drive_client):
        """Test handling of permission denied errors."""
        permission_error = HttpError(
            resp=Mock(status=403),
            content=b'{"error": {"code": 403, "message": "Permission denied"}}',
        )

        mock_drive_client.files().list().execute.side_effect = permission_error

        with pytest.raises(HttpError):
            drive_service.list_files_in_folder("restricted-folder")

    def test_rate_limit_handling(self, drive_service, mock_retry_handler):
        """Test handling of rate limit errors."""
        rate_limit_error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429, "message": "Rate limit exceeded"}}',
        )

        mock_retry_handler.execute_with_retry.side_effect = rate_limit_error

        with pytest.raises(HttpError):
            drive_service.list_files_in_folder("test-folder-id")

    def test_malformed_query_handling(self, drive_service, mock_drive_client):
        """Test handling of malformed query errors."""
        bad_request_error = HttpError(
            resp=Mock(status=400),
            content=b'{"error": {"code": 400, "message": "Invalid query"}}',
        )

        mock_drive_client.files().list().execute.side_effect = bad_request_error

        with pytest.raises(HttpError):
            drive_service.search_files_by_name_pattern("invalid[query")


class TestGoogleDriveServiceCaching:
    """Test caching behavior for performance optimization."""

    @pytest.fixture
    def mock_drive_client(self):
        """Mock Google Drive API client."""
        mock_client = Mock()
        mock_files = Mock()
        mock_client.files.return_value = mock_files
        return mock_client

    @pytest.fixture
    def mock_retry_handler(self):
        """Mock retry handler."""
        mock_handler = Mock(spec=RetryHandler)
        mock_handler.execute_with_retry.side_effect = (
            lambda func, *args, **kwargs: func(*args, **kwargs)
        )
        return mock_handler

    @pytest.fixture
    def drive_service(self, mock_drive_client, mock_retry_handler):
        """GoogleDriveService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_drive_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_build.return_value = mock_drive_client
        mock_auth.return_value = (Mock(), "test-project")

        service = GoogleDriveService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_metadata_caching(self, drive_service, mock_drive_client):
        """Test that file metadata is cached appropriately."""
        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        # First call
        result1 = drive_service.get_file_metadata("file123")
        # Second call should use cache
        result2 = drive_service.get_file_metadata("file123")

        assert result1 == result2
        # API should only be called once due to caching
        assert mock_drive_client.files().get().execute.call_count == 1

    def test_folder_listing_caching(self, drive_service, mock_drive_client):
        """Test that folder listings are cached for performance."""
        mock_response = {"files": [{"id": "file1", "name": "File1.xlsx"}]}
        mock_drive_client.files().list().execute.return_value = mock_response

        # First call
        result1 = drive_service.list_files_in_folder("folder123")
        # Second call should use cache
        result2 = drive_service.list_files_in_folder("folder123")

        assert result1 == result2
        # API should only be called once due to caching
        assert mock_drive_client.files().list().execute.call_count == 1


class TestGetModificationTime:
    """Test get_modification_time method for cache invalidation."""

    @pytest.fixture
    def mock_drive_client(self):
        """Mock Google Drive API client."""
        mock_client = Mock()
        mock_files = Mock()
        mock_client.files.return_value = mock_files
        return mock_client

    @pytest.fixture
    def mock_retry_handler(self):
        """Mock retry handler."""
        mock_handler = Mock(spec=RetryHandler)
        mock_handler.execute_with_retry.side_effect = (
            lambda func, *args, **kwargs: func(*args, **kwargs)
        )
        return mock_handler

    @pytest.fixture
    def drive_service(self, mock_drive_client, mock_retry_handler):
        """GoogleDriveService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_drive_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_build.return_value = mock_drive_client
        mock_auth.return_value = (Mock(), "test-project")

        service = GoogleDriveService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_get_modification_time_success(self, drive_service, mock_drive_client):
        """Test getting modification time from file metadata."""
        from datetime import datetime

        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            "modifiedTime": "2025-10-05T10:00:00.000Z",
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        mod_time = drive_service.get_modification_time("file123")

        assert isinstance(mod_time, datetime)
        assert mod_time.year == 2025
        assert mod_time.month == 10
        assert mod_time.day == 5
        assert mod_time.hour == 10
        assert mod_time.minute == 0

    def test_get_modification_time_rfc3339_parsing(
        self, drive_service, mock_drive_client
    ):
        """Test parsing of RFC 3339 timestamp format."""
        from datetime import datetime

        # Test various RFC 3339 formats
        test_cases = [
            ("2025-10-05T10:00:00.000Z", datetime(2025, 10, 5, 10, 0, 0)),
            ("2025-12-31T23:59:59.999Z", datetime(2025, 12, 31, 23, 59, 59, 999000)),
        ]

        for timestamp_str, expected_dt in test_cases:
            mock_response = {
                "id": "file123",
                "name": "Test_File.xlsx",
                "modifiedTime": timestamp_str,
            }
            mock_drive_client.files().get().execute.return_value = mock_response

            # Clear cache to force new read
            drive_service._metadata_cache.clear()

            mod_time = drive_service.get_modification_time("file123")

            # Compare up to seconds (ignore microseconds for simpler comparison)
            assert mod_time.year == expected_dt.year
            assert mod_time.month == expected_dt.month
            assert mod_time.day == expected_dt.day
            assert mod_time.hour == expected_dt.hour
            assert mod_time.minute == expected_dt.minute
            assert mod_time.second == expected_dt.second

    def test_get_modification_time_missing_field(
        self, drive_service, mock_drive_client
    ):
        """Test error handling when modifiedTime field is missing."""
        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            # modifiedTime missing
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        with pytest.raises(ValueError, match="No modification time available"):
            drive_service.get_modification_time("file123")

    def test_get_modification_time_invalid_format(
        self, drive_service, mock_drive_client
    ):
        """Test error handling for invalid timestamp format."""
        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            "modifiedTime": "invalid-timestamp",
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        with pytest.raises(ValueError):
            drive_service.get_modification_time("file123")

    def test_get_modification_time_uses_cache(self, drive_service, mock_drive_client):
        """Test that get_modification_time uses metadata cache."""
        mock_response = {
            "id": "file123",
            "name": "Test_File.xlsx",
            "modifiedTime": "2025-10-05T10:00:00.000Z",
        }
        mock_drive_client.files().get().execute.return_value = mock_response

        # First call
        drive_service.get_modification_time("file123")
        # Second call should use cache
        drive_service.get_modification_time("file123")

        # API should only be called once due to caching
        assert mock_drive_client.files().get().execute.call_count == 1
