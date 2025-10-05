"""Unit tests for list-timesheets command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.commands.list import list_timesheets


class TestListTimesheetsCommand:
    """Test suite for list-timesheets command."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_list_timesheets_no_args(self, runner):
        """Test listing timesheets without arguments."""
        with patch("src.cli.commands.list.get_config"), patch(
            "src.cli.commands.list.GoogleDriveService"
        ) as mock_drive:
            # Mock list_files_in_folder to return sample data
            mock_service = MagicMock()
            mock_service.list_files_in_folder.return_value = [
                {
                    "name": "Timesheet_John_Doe",
                    "id": "abc123",
                    "modifiedTime": "2024-10-01T10:00:00Z",
                }
            ]
            mock_drive.return_value = mock_service

            result = runner.invoke(list_timesheets, [])
            assert result.exit_code == 0
            # Should show table with data
            assert "Freelancer" in result.output or "File" in result.output

    def test_list_timesheets_with_folder_id(self, runner):
        """Test listing timesheets with custom folder ID."""
        with patch("src.cli.commands.list.get_config"), patch(
            "src.cli.commands.list.GoogleDriveService"
        ) as mock_drive:
            mock_service = MagicMock()
            mock_service.list_files_in_folder.return_value = []
            mock_drive.return_value = mock_service

            result = runner.invoke(list_timesheets, ["--folder-id", "custom123"])
            assert result.exit_code == 0

    def test_list_timesheets_handles_errors(self, runner):
        """Test error handling when listing fails."""
        with patch("src.cli.commands.list.get_config"), patch(
            "src.cli.commands.list.GoogleDriveService"
        ) as mock_drive:
            mock_service = MagicMock()
            mock_service.list_files_in_folder.side_effect = Exception("API Error")
            mock_drive.return_value = mock_service

            result = runner.invoke(list_timesheets, [])
            assert result.exit_code != 0
            assert "error" in result.output.lower() or "failed" in result.output.lower()
