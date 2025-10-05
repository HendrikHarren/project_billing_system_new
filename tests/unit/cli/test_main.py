"""Unit tests for CLI main entry point."""

import pytest
from click.testing import CliRunner

from src.cli import cli


class TestCLIMain:
    """Test suite for CLI main entry point."""

    @pytest.fixture
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    def test_cli_group_exists(self, runner):
        """Test that CLI group exists and can be invoked."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_cli_help_text(self, runner):
        """Test that CLI help text is informative."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Billing System CLI" in result.output
        assert "Commands:" in result.output

    def test_cli_version_flag(self, runner):
        """Test that --version flag works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_cli_has_generate_report_command(self, runner):
        """Test that generate-report command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "generate-report" in result.output

    def test_cli_has_list_timesheets_command(self, runner):
        """Test that list-timesheets command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "list-timesheets" in result.output

    def test_cli_has_validate_data_command(self, runner):
        """Test that validate-data command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "validate-data" in result.output

    def test_unknown_command_shows_error(self, runner):
        """Test that unknown commands show helpful error."""
        result = runner.invoke(cli, ["unknown-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output or "Error" in result.output
