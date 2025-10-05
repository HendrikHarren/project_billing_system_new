"""Unit tests for generate-report command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.cli.commands.generate import generate_report


class TestGenerateReportCommand:
    """Test suite for generate-report command."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_services(self):
        """Create mocked services for testing."""
        with patch("src.cli.commands.generate.GoogleDriveService") as mock_drive, patch(
            "src.cli.commands.generate.TimesheetAggregator"
        ) as mock_aggregator, patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ) as mock_generator, patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ) as mock_writer:
            yield {
                "drive": mock_drive,
                "aggregator": mock_aggregator,
                "generator": mock_generator,
                "writer": mock_writer,
            }

    def test_generate_report_requires_month(self, runner):
        """Test that month parameter is required."""
        result = runner.invoke(generate_report, [])
        assert result.exit_code != 0
        assert "month" in result.output.lower() or "required" in result.output.lower()

    def test_generate_report_validates_month_format(self, runner):
        """Test that month format is validated."""
        result = runner.invoke(generate_report, ["--month", "invalid"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "format" in result.output.lower()

    def test_generate_report_accepts_valid_month(self, runner):
        """Test that valid month format is accepted."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(generate_report, ["--month", "2024-10"])
            # Command should start processing
            assert "2024-10" in result.output or result.exit_code == 0

    def test_generate_report_accepts_project_filter(self, runner):
        """Test that project filter is accepted."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(
                generate_report, ["--month", "2024-10", "--project", "PROJ001"]
            )
            assert "PROJ001" in result.output or result.exit_code == 0

    def test_generate_report_accepts_freelancer_filter(self, runner):
        """Test that freelancer filter is accepted."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(
                generate_report, ["--month", "2024-10", "--freelancer", "John Doe"]
            )
            assert "John Doe" in result.output or result.exit_code == 0

    def test_generate_report_shows_progress(self, runner):
        """Test that progress indicators are shown."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(generate_report, ["--month", "2024-10"])
            # Should show stage information
            assert "1/" in result.output or "Reading" in result.output
