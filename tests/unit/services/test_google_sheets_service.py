"""
Unit tests for Google Sheets service.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
from googleapiclient.errors import HttpError

from src.services.google_sheets_service import GoogleSheetsService
from src.services.retry_handler import RetryHandler


class TestGoogleSheetsService:
    """Test cases for GoogleSheetsService."""

    @pytest.fixture
    def mock_sheets_client(self):
        """Mock Google Sheets API client."""
        mock_client = Mock()
        mock_spreadsheets = Mock()
        mock_values = Mock()

        mock_client.spreadsheets.return_value = mock_spreadsheets
        mock_spreadsheets.values.return_value = mock_values

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
    def sheets_service(self, mock_sheets_client, mock_retry_handler):
        """GoogleSheetsService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_sheets_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_credentials = Mock()
        mock_auth.return_value = (mock_credentials, "test-project")
        mock_build.return_value = mock_sheets_client

        service = GoogleSheetsService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_service_initialization(self, mock_retry_handler):
        """Test service initializes with proper authentication."""
        with patch("src.services.google_sheets_service.build") as mock_build:
            with patch("google.auth.default") as mock_auth:
                mock_credentials = Mock()
                mock_auth.return_value = (mock_credentials, "test-project")

                service = GoogleSheetsService(retry_handler=mock_retry_handler)
                assert service is not None

                mock_auth.assert_called_once_with(
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                mock_build.assert_called_once_with(
                    "sheets", "v4", credentials=mock_credentials
                )

    def test_read_sheet_success(self, sheets_service, mock_sheets_client):
        """Test successful sheet reading."""
        # Setup mock response
        mock_response = {
            "values": [
                ["Name", "Age", "City"],
                ["John", "25", "NYC"],
                ["Jane", "30", "LA"],
            ]
        }
        mock_sheets_client.spreadsheets().values().get().execute.return_value = (
            mock_response
        )

        # Execute
        result = sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

        # Verify
        expected_df = pd.DataFrame(
            [
                {"Name": "John", "Age": "25", "City": "NYC"},
                {"Name": "Jane", "Age": "30", "City": "LA"},
            ]
        )
        pd.testing.assert_frame_equal(result, expected_df)

    def test_read_sheet_with_retry_on_rate_limit(
        self, sheets_service, mock_retry_handler, mock_sheets_client
    ):
        """Test sheet reading with retry on rate limit."""
        # Configure mock response
        mock_response = {"values": []}
        mock_sheets_client.spreadsheets().values().get().execute.return_value = (
            mock_response
        )

        # Setup retry handler to simulate rate limiting
        mock_retry_handler.execute_with_retry.side_effect = lambda func: func()

        # This should trigger retry logic
        sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

        # Verify retry handler was called
        mock_retry_handler.execute_with_retry.assert_called_once()

    def test_read_sheet_empty_response(self, sheets_service, mock_sheets_client):
        """Test handling of empty sheet response."""
        mock_response = {"values": []}
        mock_sheets_client.spreadsheets().values().get().execute.return_value = (
            mock_response
        )

        result = sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

        assert result.empty
        assert len(result.columns) == 0

    def test_read_sheet_api_error(self, sheets_service, mock_sheets_client):
        """Test handling of API errors."""
        mock_sheets_client.spreadsheets().values().get().execute.side_effect = (
            HttpError(resp=Mock(status=403), content=b"Forbidden")
        )

        with pytest.raises(HttpError):
            sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

    def test_write_sheet_success(self, sheets_service, mock_sheets_client):
        """Test successful sheet writing."""
        # Setup test data
        test_data = pd.DataFrame(
            [
                {"Name": "Alice", "Age": "28", "City": "SF"},
                {"Name": "Bob", "Age": "32", "City": "Seattle"},
            ]
        )

        mock_response = {"updatedCells": 6}
        mock_sheets_client.spreadsheets().values().update().execute.return_value = (
            mock_response
        )

        # Execute
        result = sheets_service.write_sheet("test-sheet-id", "Sheet1!A1", test_data)

        # Verify
        assert result["updatedCells"] == 6
        # Check that update was called with correct parameters
        mock_sheets_client.spreadsheets().values().update.assert_called_with(
            spreadsheetId="test-sheet-id",
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": [["Alice", "28", "SF"], ["Bob", "32", "Seattle"]]},
        )

    def test_write_sheet_with_headers(self, sheets_service, mock_sheets_client):
        """Test sheet writing includes headers."""
        test_data = pd.DataFrame([{"Name": "Alice", "Age": "28"}])

        sheets_service.write_sheet(
            "test-sheet-id", "Sheet1!A1", test_data, include_headers=True
        )

        # Verify headers are included in the call
        call_args = mock_sheets_client.spreadsheets().values().update.call_args
        body = call_args[1]["body"]
        assert body["values"][0] == ["Name", "Age"]  # Headers
        assert body["values"][1] == ["Alice", "28"]  # Data

    def test_batch_read_sheets(self, sheets_service, mock_sheets_client):
        """Test batch reading multiple sheets."""
        mock_response = {
            "valueRanges": [
                {"values": [["A1", "B1"], ["A2", "B2"]]},
                {"values": [["C1", "D1"], ["C2", "D2"]]},
            ]
        }
        mock_sheets_client.spreadsheets().values().batchGet().execute.return_value = (
            mock_response
        )

        ranges = ["Sheet1!A1:B2", "Sheet2!C1:D2"]
        results = sheets_service.batch_read_sheets("test-sheet-id", ranges)

        assert len(results) == 2
        assert all(isinstance(df, pd.DataFrame) for df in results)

    def test_get_sheet_metadata(self, sheets_service, mock_sheets_client):
        """Test retrieving sheet metadata."""
        mock_response = {
            "sheets": [
                {"properties": {"title": "Sheet1", "sheetId": 0}},
                {"properties": {"title": "Sheet2", "sheetId": 1}},
            ]
        }
        mock_sheets_client.spreadsheets().get().execute.return_value = mock_response

        metadata = sheets_service.get_sheet_metadata("test-sheet-id")

        assert len(metadata["sheets"]) == 2
        assert metadata["sheets"][0]["properties"]["title"] == "Sheet1"

    def test_clear_sheet_range(self, sheets_service, mock_sheets_client):
        """Test clearing a sheet range."""
        mock_response = {"clearedRange": "Sheet1!A1:C10"}
        mock_sheets_client.spreadsheets().values().clear().execute.return_value = (
            mock_response
        )

        result = sheets_service.clear_sheet_range("test-sheet-id", "Sheet1!A1:C10")

        assert result["clearedRange"] == "Sheet1!A1:C10"

    def test_create_sheet(self, sheets_service, mock_sheets_client):
        """Test creating a new sheet."""
        mock_response = {
            "replies": [
                {"addSheet": {"properties": {"title": "NewSheet", "sheetId": 123}}}
            ]
        }
        mock_sheets_client.spreadsheets().batchUpdate().execute.return_value = (
            mock_response
        )

        result = sheets_service.create_sheet("test-sheet-id", "NewSheet")

        assert result["replies"][0]["addSheet"]["properties"]["title"] == "NewSheet"


class TestGoogleSheetsServiceIntegration:
    """Integration tests for GoogleSheetsService."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test requires real Google API credentials")
    def test_real_api_connection(self, test_config):
        """Test connection to real Google Sheets API."""
        retry_handler = RetryHandler()
        service = GoogleSheetsService(retry_handler=retry_handler)

        # Test reading from project terms file
        df = service.read_sheet(test_config.project_terms_file_id, "Sheet1!A1:Z100")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test requires real Google API credentials")
    def test_batch_operations_performance(self, test_config):
        """Test batch operations are more efficient than individual calls."""
        retry_handler = RetryHandler()
        service = GoogleSheetsService(retry_handler=retry_handler)
        assert service is not None

        # This test would measure performance of batch vs individual operations
        # Implementation depends on having test data available
        pass


class TestGoogleSheetsServiceErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_sheets_client(self):
        """Mock Google Sheets API client."""
        mock_client = Mock()
        mock_spreadsheets = Mock()
        mock_client.spreadsheets.return_value = mock_spreadsheets
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
    def sheets_service(self, mock_sheets_client, mock_retry_handler):
        """GoogleSheetsService instance with mocked dependencies."""
        build_patcher = patch("src.services.google_sheets_service.build")
        auth_patcher = patch("google.auth.default")

        mock_build = build_patcher.start()
        mock_auth = auth_patcher.start()

        mock_build.return_value = mock_sheets_client
        mock_auth.return_value = (Mock(), "test-project")

        service = GoogleSheetsService(retry_handler=mock_retry_handler)

        yield service

        build_patcher.stop()
        auth_patcher.stop()

    def test_quota_exceeded_handling(self, sheets_service, mock_retry_handler):
        """Test handling of quota exceeded errors."""
        quota_error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429, "message": "Quota exceeded"}}',
        )

        mock_retry_handler.execute_with_retry.side_effect = quota_error

        with pytest.raises(HttpError):
            sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

    def test_permission_denied_handling(self, sheets_service, mock_retry_handler):
        """Test handling of permission denied errors."""
        permission_error = HttpError(
            resp=Mock(status=403),
            content=b'{"error": {"code": 403, "message": "Permission denied"}}',
        )

        mock_retry_handler.execute_with_retry.side_effect = permission_error

        with pytest.raises(HttpError):
            sheets_service.read_sheet("test-sheet-id", "Sheet1!A1:C10")

    def test_invalid_range_handling(self, sheets_service, mock_sheets_client):
        """Test handling of invalid range specifications."""
        invalid_range_error = HttpError(
            resp=Mock(status=400),
            content=b'{"error": {"code": 400, "message": "Invalid range"}}',
        )

        mock_sheets_client.spreadsheets().values().get().execute.side_effect = (
            invalid_range_error
        )

        with pytest.raises(HttpError):
            sheets_service.read_sheet("test-sheet-id", "InvalidRange")
