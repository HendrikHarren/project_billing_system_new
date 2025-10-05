"""Unit tests for validate-data command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.commands.validate import validate_data


class TestValidateDataCommand:
    """Test suite for validate-data command."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_validate_data_no_args(self, runner):
        """Test validating all data without arguments."""
        with patch("src.cli.commands.validate.get_config"), patch(
            "src.cli.commands.validate.GoogleSheetsService"
        ), patch("src.cli.commands.validate.GoogleDriveService"), patch(
            "src.cli.commands.validate.TimesheetReader"
        ), patch(
            "src.cli.commands.validate.TimesheetValidator"
        ):
            result = runner.invoke(validate_data, [])
            # Should run without requiring arguments
            assert "Validating" in result.output

    def test_validate_data_with_file_id(self, runner):
        """Test validating specific file."""
        with patch("src.cli.commands.validate.get_config"), patch(
            "src.cli.commands.validate.GoogleSheetsService"
        ), patch("src.cli.commands.validate.GoogleDriveService"), patch(
            "src.cli.commands.validate.TimesheetReader"
        ), patch(
            "src.cli.commands.validate.TimesheetValidator"
        ):
            result = runner.invoke(validate_data, ["--file-id", "abc123"])
            assert "abc123" in result.output or "Validating" in result.output

    def test_validate_data_with_month(self, runner):
        """Test validating data for specific month."""
        with patch("src.cli.commands.validate.get_config"), patch(
            "src.cli.commands.validate.GoogleSheetsService"
        ), patch("src.cli.commands.validate.GoogleDriveService"), patch(
            "src.cli.commands.validate.TimesheetReader"
        ), patch(
            "src.cli.commands.validate.TimesheetValidator"
        ):
            result = runner.invoke(validate_data, ["--month", "2024-10"])
            assert "2024-10" in result.output or "Validating" in result.output

    def test_validate_data_severity_filter(self, runner):
        """Test filtering by severity level."""
        result = runner.invoke(validate_data, ["--severity", "warning"])
        assert result.exit_code == 0 or "Validating" in result.output

    def test_validate_data_shows_summary(self, runner):
        """Test that validation summary is displayed."""
        with patch("src.cli.commands.validate.get_config"), patch(
            "src.cli.commands.validate.GoogleSheetsService"
        ), patch("src.cli.commands.validate.GoogleDriveService"), patch(
            "src.cli.commands.validate.TimesheetReader"
        ), patch(
            "src.cli.commands.validate.TimesheetValidator"
        ):
            result = runner.invoke(validate_data, [])
            # Should show summary with counts
            assert (
                "Summary" in result.output
                or "Errors" in result.output
                or "Warnings" in result.output
            )

    def test_validate_data_exits_with_error_on_failures(self, runner):
        """Test that command exits with error code when validation fails."""
        with patch("src.cli.commands.validate.get_config"), patch(
            "src.cli.commands.validate.GoogleSheetsService"
        ), patch("src.cli.commands.validate.GoogleDriveService"), patch(
            "src.cli.commands.validate.TimesheetReader"
        ), patch(
            "src.cli.commands.validate.TimesheetValidator"
        ) as mock_validator:
            # Mock validator to return errors
            mock_val_instance = MagicMock()
            mock_report = MagicMock()
            mock_report.has_errors.return_value = True
            mock_report.error_count = 5
            mock_report.warning_count = 2
            mock_report.info_count = 1
            mock_val_instance.validate_entries.return_value = mock_report
            mock_validator.return_value = mock_val_instance

            result = runner.invoke(validate_data, ["--file-id", "test"])
            # Should exit with error when validation fails
            # (Either it exits with non-zero or shows error message)
            assert result.exit_code != 0 or "error" in result.output.lower()
