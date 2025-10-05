"""Unit tests for CLI output formatters."""

from src.cli.utils.formatters import (
    format_error,
    format_info,
    format_success,
    format_table,
    format_warning,
)


class TestFormatters:
    """Test suite for CLI output formatters."""

    def test_format_success_contains_message(self):
        """Test that success formatter includes the message."""
        result = format_success("Operation completed")
        assert "Operation completed" in result

    def test_format_error_contains_message(self):
        """Test that error formatter includes the message."""
        result = format_error("Something went wrong")
        assert "Something went wrong" in result

    def test_format_warning_contains_message(self):
        """Test that warning formatter includes the message."""
        result = format_warning("This is a warning")
        assert "This is a warning" in result

    def test_format_info_contains_message(self):
        """Test that info formatter includes the message."""
        result = format_info("Information message")
        assert "Information message" in result

    def test_format_table_with_headers_and_rows(self):
        """Test table formatting with headers and data."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "30", "New York"],
            ["Bob", "25", "London"],
        ]
        result = format_table(headers, rows)
        assert "Name" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_format_table_with_empty_rows(self):
        """Test table formatting with no data rows."""
        headers = ["Name", "Age"]
        rows = []
        result = format_table(headers, rows)
        assert "Name" in result
        assert "Age" in result

    def test_format_table_handles_long_values(self):
        """Test table formatting with long cell values."""
        headers = ["Description"]
        rows = [["This is a very long description that might need truncation"]]
        result = format_table(headers, rows)
        assert "Description" in result
