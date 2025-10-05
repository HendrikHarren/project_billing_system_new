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

    def test_generate_report_uses_defaults_without_month(self, runner):
        """Test that command uses default date range when month not provided."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(generate_report, [])
            # Should use default date range (current + previous year)
            assert "default" in result.output.lower() or "2024" in result.output

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

    def test_generate_report_accepts_date_range(self, runner):
        """Test that date-range parameter is accepted."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(
                generate_report, ["--date-range", "2023-01", "2024-12"]
            )
            assert "2023-01" in result.output or "2024-12" in result.output

    def test_generate_report_accepts_start_end_dates(self, runner):
        """Test that start-date and end-date parameters are accepted."""
        with patch("src.cli.commands.generate.get_config"), patch(
            "src.cli.commands.generate.GoogleDriveService"
        ), patch("src.cli.commands.generate.TimesheetAggregator"), patch(
            "src.cli.commands.generate.MasterTimesheetGenerator"
        ), patch(
            "src.cli.commands.generate.GoogleSheetsWriter"
        ):
            result = runner.invoke(
                generate_report,
                ["--start-date", "2024-01-01", "--end-date", "2024-06-30"],
            )
            assert "2024-01-01" in result.output or "2024-06-30" in result.output

    def test_generate_report_rejects_conflicting_date_options(self, runner):
        """Test that conflicting date options are rejected."""
        result = runner.invoke(
            generate_report,
            ["--month", "2024-10", "--date-range", "2023-01", "2024-12"],
        )
        assert result.exit_code != 0
        assert "multiple" in result.output.lower() or "cannot" in result.output.lower()

    def test_generate_report_requires_both_start_and_end(self, runner):
        """Test that start-date requires end-date and vice versa."""
        result = runner.invoke(generate_report, ["--start-date", "2024-01-01"])
        assert result.exit_code != 0
        assert "together" in result.output.lower() or "must" in result.output.lower()

    def test_generate_report_validates_start_before_end(self, runner):
        """Test that start-date must be before end-date."""
        result = runner.invoke(
            generate_report,
            ["--start-date", "2024-12-31", "--end-date", "2024-01-01"],
        )
        assert result.exit_code != 0
        assert "before" in result.output.lower() or "after" in result.output.lower()
