"""Unit tests for TimesheetReader."""

from datetime import date, time
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.readers.timesheet_reader import TimesheetReader


class TestTimesheetReader:
    """Test TimesheetReader functionality."""

    @pytest.fixture
    def mock_sheets_service(self):
        """Create a mock Google Sheets service."""
        return Mock()

    @pytest.fixture
    def timesheet_reader(self, mock_sheets_service):
        """Create a TimesheetReader instance with mocked service."""
        return TimesheetReader(mock_sheets_service)

    @pytest.fixture
    def sample_sheet_metadata(self):
        """Sample sheet metadata with freelancer name."""
        return {
            "properties": {"title": "John_Doe_Timesheet"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Timesheet"}}],
        }

    @pytest.fixture
    def sample_timesheet_data(self):
        """Sample timesheet data from Google Sheets.

        Note: First row is example row (row 2 in actual sheet) that gets skipped.
        """
        return pd.DataFrame(
            [
                {
                    # Row 2 (example row) - this will be skipped by the reader
                    "Date": "2023-01-01",
                    "Project": "EXAMPLE",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Example",
                    "Break": "00:30",
                    "Travel time": "00:00",
                    "Sum": "07:30",
                },
                {
                    # Row 3 (actual data)
                    "Date": "2023-06-15",
                    "Project": "PROJ-001",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Development work",
                    "Break": "00:30",
                    "Travel time": "01:00",
                    "Sum": "08:30",
                },
                {
                    # Row 4 (actual data)
                    "Date": "2023-06-16",
                    "Project": "PROJ-002",
                    "Location": "Off-site",
                    "Start Time": "10:00",
                    "End Time": "18:00",
                    "Topics worked on": "Code review",
                    "Break": "01:00",
                    "Travel time": "00:00",
                    "Sum": "07:00",
                },
            ]
        )

    def test_init(self, mock_sheets_service):
        """Test TimesheetReader initialization."""
        reader = TimesheetReader(mock_sheets_service)
        assert reader.sheets_service == mock_sheets_service

    def test_extract_freelancer_name_from_title(self, timesheet_reader):
        """Test extracting freelancer name from sheet title."""
        metadata = {"properties": {"title": "John_Doe_Timesheet"}}
        name = timesheet_reader._extract_freelancer_name(metadata)
        assert name == "John Doe"

    def test_extract_freelancer_name_with_underscores(self, timesheet_reader):
        """Test extracting freelancer name with multiple underscores."""
        metadata = {"properties": {"title": "Jane_Mary_Smith_Timesheet"}}
        name = timesheet_reader._extract_freelancer_name(metadata)
        assert name == "Jane Mary Smith"

    def test_extract_freelancer_name_without_timesheet_suffix(self, timesheet_reader):
        """Test extracting freelancer name when suffix is missing."""
        metadata = {"properties": {"title": "John_Doe"}}
        name = timesheet_reader._extract_freelancer_name(metadata)
        assert name == "John Doe"

    def test_parse_date_iso_format(self, timesheet_reader):
        """Test parsing date in ISO format (YYYY-MM-DD)."""
        result = timesheet_reader._parse_date("2023-06-15")
        assert result == date(2023, 6, 15)

    def test_parse_date_european_format(self, timesheet_reader):
        """Test parsing date in European format (DD.MM.YYYY)."""
        result = timesheet_reader._parse_date("15.06.2023")
        assert result == date(2023, 6, 15)

    def test_parse_date_us_format(self, timesheet_reader):
        """Test parsing date in US format (MM/DD/YYYY)."""
        result = timesheet_reader._parse_date("06/15/2023")
        assert result == date(2023, 6, 15)

    def test_parse_date_invalid_raises_error(self, timesheet_reader):
        """Test parsing invalid date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            timesheet_reader._parse_date("invalid-date")

    def test_parse_time_standard_format(self, timesheet_reader):
        """Test parsing time in HH:MM format."""
        result = timesheet_reader._parse_time("09:30")
        assert result == time(9, 30)

    def test_parse_time_single_digit_hour(self, timesheet_reader):
        """Test parsing time with single digit hour."""
        result = timesheet_reader._parse_time("9:30")
        assert result == time(9, 30)

    def test_parse_time_midnight(self, timesheet_reader):
        """Test parsing midnight time."""
        result = timesheet_reader._parse_time("00:00")
        assert result == time(0, 0)

    def test_parse_time_invalid_raises_error(self, timesheet_reader):
        """Test parsing invalid time raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            timesheet_reader._parse_time("25:99")

    def test_normalize_location_onsite(self, timesheet_reader):
        """Test normalizing 'On-site' location."""
        result = timesheet_reader._normalize_location("On-site")
        assert result == "onsite"

    def test_normalize_location_offsite(self, timesheet_reader):
        """Test normalizing 'Off-site' location."""
        result = timesheet_reader._normalize_location("Off-site")
        assert result == "remote"

    def test_normalize_location_case_insensitive(self, timesheet_reader):
        """Test location normalization is case insensitive."""
        assert timesheet_reader._normalize_location("ON-SITE") == "onsite"
        assert timesheet_reader._normalize_location("off-site") == "remote"

    def test_normalize_location_with_prefix(self, timesheet_reader):
        """Test normalizing location with location prefix like 'Munich On-site'."""
        result = timesheet_reader._normalize_location("Munich On-site")
        assert result == "onsite"

    def test_normalize_location_invalid_raises_error(self, timesheet_reader):
        """Test invalid location raises ValueError."""
        with pytest.raises(ValueError, match="Invalid location"):
            timesheet_reader._normalize_location("hybrid")

    def test_time_to_minutes_standard(self, timesheet_reader):
        """Test converting time string to minutes."""
        result = timesheet_reader._time_to_minutes("01:30")
        assert result == 90

    def test_time_to_minutes_zero(self, timesheet_reader):
        """Test converting zero time to minutes."""
        result = timesheet_reader._time_to_minutes("00:00")
        assert result == 0

    def test_time_to_minutes_hours_only(self, timesheet_reader):
        """Test converting hours-only time to minutes."""
        result = timesheet_reader._time_to_minutes("02:00")
        assert result == 120

    def test_parse_row_valid_data(self, timesheet_reader):
        """Test parsing a valid timesheet row."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "Development",
            "Break": "00:30",
            "Travel time": "01:00",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)

        assert entry is not None
        assert entry.freelancer_name == "John Doe"
        assert entry.date == date(2023, 6, 15)
        assert entry.project_code == "PROJ-001"
        assert entry.start_time == time(9, 0)
        assert entry.end_time == time(17, 0)
        assert entry.location == "onsite"
        assert entry.break_minutes == 30
        assert entry.travel_time_minutes == 60
        assert entry.notes == "Development"

    def test_parse_row_with_empty_notes(self, timesheet_reader):
        """Test parsing row with empty notes field."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)

        assert entry is not None
        assert entry.notes is None

    def test_parse_row_empty_row_returns_none(self, timesheet_reader):
        """Test parsing empty row returns None."""
        row = {
            "Date": "",
            "Project": "",
            "Location": "",
            "Start Time": "",
            "End Time": "",
            "Topics worked on": "",
            "Break": "",
            "Travel time": "",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)
        assert entry is None

    def test_parse_row_missing_date_returns_none(self, timesheet_reader):
        """Test parsing row with missing date returns None."""
        row = {
            "Date": "",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "Work",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)
        assert entry is None

    def test_parse_row_invalid_date_returns_none(self, timesheet_reader):
        """Test parsing row with invalid date returns None and logs warning."""
        row = {
            "Date": "invalid-date",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "Work",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        with patch("src.readers.timesheet_reader.logger") as mock_logger:
            entry = timesheet_reader._parse_row(row, freelancer_name)
            assert entry is None
            mock_logger.warning.assert_called()

    def test_parse_row_overnight_shift(self, timesheet_reader):
        """Test parsing row with overnight shift (end < start)."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "22:00",
            "End Time": "06:00",
            "Topics worked on": "Night shift",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)

        assert entry is not None
        assert entry.start_time == time(22, 0)
        assert entry.end_time == time(6, 0)
        assert entry.is_overnight is True

    def test_read_timesheet_success(
        self,
        timesheet_reader,
        mock_sheets_service,
        sample_sheet_metadata,
        sample_timesheet_data,
    ):
        """Test successfully reading timesheet data."""
        spreadsheet_id = "test-spreadsheet-id"

        # Mock the service calls
        mock_sheets_service.get_sheet_metadata.return_value = sample_sheet_metadata
        mock_sheets_service.read_sheet.return_value = sample_timesheet_data

        entries = timesheet_reader.read_timesheet(spreadsheet_id)

        assert len(entries) == 2
        assert entries[0].freelancer_name == "John Doe"
        assert entries[0].project_code == "PROJ-001"
        assert entries[0].location == "onsite"
        assert entries[1].project_code == "PROJ-002"
        assert entries[1].location == "remote"

        # Verify service was called correctly
        mock_sheets_service.get_sheet_metadata.assert_called_once_with(spreadsheet_id)
        mock_sheets_service.read_sheet.assert_called_once()

    def test_read_timesheet_empty_sheet(
        self, timesheet_reader, mock_sheets_service, sample_sheet_metadata
    ):
        """Test reading empty timesheet returns empty list."""
        spreadsheet_id = "test-spreadsheet-id"

        # Mock empty data
        mock_sheets_service.get_sheet_metadata.return_value = sample_sheet_metadata
        mock_sheets_service.read_sheet.return_value = pd.DataFrame()

        entries = timesheet_reader.read_timesheet(spreadsheet_id)

        assert entries == []

    def test_read_timesheet_with_invalid_rows(
        self, timesheet_reader, mock_sheets_service, sample_sheet_metadata
    ):
        """Test reading timesheet skips invalid rows."""
        spreadsheet_id = "test-spreadsheet-id"

        # Mix of valid and invalid data (first row is example that gets skipped)
        data = pd.DataFrame(
            [
                {
                    # Row 2 (example row) - will be skipped
                    "Date": "2023-01-01",
                    "Project": "EXAMPLE",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Example",
                    "Break": "00:30",
                    "Travel time": "00:00",
                },
                {
                    # Row 3 (actual data - valid)
                    "Date": "2023-06-15",
                    "Project": "PROJ-001",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Work",
                    "Break": "00:30",
                    "Travel time": "00:00",
                },
                {
                    # Row 4 (invalid - empty date, should be skipped)
                    "Date": "",
                    "Project": "PROJ-002",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Work",
                    "Break": "00:30",
                    "Travel time": "00:00",
                },
                {
                    # Row 5 (actual data - valid)
                    "Date": "2023-06-17",
                    "Project": "PROJ-003",
                    "Location": "Off-site",
                    "Start Time": "10:00",
                    "End Time": "18:00",
                    "Topics worked on": "Review",
                    "Break": "01:00",
                    "Travel time": "00:00",
                },
            ]
        )

        mock_sheets_service.get_sheet_metadata.return_value = sample_sheet_metadata
        mock_sheets_service.read_sheet.return_value = data

        entries = timesheet_reader.read_timesheet(spreadsheet_id)

        # Should only get 2 valid entries
        assert len(entries) == 2
        assert entries[0].date == date(2023, 6, 15)
        assert entries[1].date == date(2023, 6, 17)

    def test_read_timesheet_handles_extra_columns(
        self, timesheet_reader, mock_sheets_service, sample_sheet_metadata
    ):
        """Test reading timesheet handles extra columns gracefully."""
        spreadsheet_id = "test-spreadsheet-id"

        # Data with extra column (row 1 is example, row 2 is actual data)
        data = pd.DataFrame(
            [
                {
                    # Row 2 (example row) - will be skipped
                    "Date": "2023-01-01",
                    "Project": "EXAMPLE",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Example",
                    "Break": "00:30",
                    "Travel time": "00:00",
                    "Extra Column": "Example",
                },
                {
                    # Row 3 (actual data)
                    "Date": "2023-06-15",
                    "Project": "PROJ-001",
                    "Location": "On-site",
                    "Start Time": "09:00",
                    "End Time": "17:00",
                    "Topics worked on": "Work",
                    "Break": "00:30",
                    "Travel time": "00:00",
                    "Extra Column": "Extra data",  # Extra column should be ignored
                },
            ]
        )

        mock_sheets_service.get_sheet_metadata.return_value = sample_sheet_metadata
        mock_sheets_service.read_sheet.return_value = data

        entries = timesheet_reader.read_timesheet(spreadsheet_id)

        assert len(entries) == 1
        assert entries[0].project_code == "PROJ-001"

    def test_read_timesheet_default_range(self, timesheet_reader, mock_sheets_service):
        """Test that read_timesheet uses correct default range."""
        spreadsheet_id = "test-spreadsheet-id"

        mock_sheets_service.get_sheet_metadata.return_value = {
            "properties": {"title": "Test_Freelancer_Timesheet"}
        }
        mock_sheets_service.read_sheet.return_value = pd.DataFrame()

        timesheet_reader.read_timesheet(spreadsheet_id)

        # Verify it reads from row 1 (includes headers, skips row 2 in code)
        call_args = mock_sheets_service.read_sheet.call_args
        assert (
            "Timesheet!A1:I" in call_args[0]
            or call_args[1].get("range_name") == "Timesheet!A1:I"
        )

    def test_parse_row_whitespace_handling(self, timesheet_reader):
        """Test parsing row handles whitespace in fields."""
        row = {
            "Date": " 2023-06-15 ",
            "Project": " PROJ-001 ",
            "Location": " On-site ",
            "Start Time": " 09:00 ",
            "End Time": " 17:00 ",
            "Topics worked on": " Development work ",
            "Break": " 00:30 ",
            "Travel time": " 00:00 ",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)

        assert entry is not None
        assert entry.project_code == "PROJ-001"
        assert entry.notes == "Development work"

    def test_parse_row_missing_optional_fields(self, timesheet_reader):
        """Test parsing row with missing optional fields uses defaults."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "",
            "Break": "00:00",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        entry = timesheet_reader._parse_row(row, freelancer_name)

        assert entry is not None
        assert entry.break_minutes == 0
        assert entry.travel_time_minutes == 0
        assert entry.notes is None

    def test_parse_row_invalid_time_returns_none(self, timesheet_reader):
        """Test parsing row with invalid time returns None."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "On-site",
            "Start Time": "invalid",
            "End Time": "17:00",
            "Topics worked on": "Work",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        with patch("src.readers.timesheet_reader.logger") as mock_logger:
            entry = timesheet_reader._parse_row(row, freelancer_name)
            assert entry is None
            mock_logger.warning.assert_called()

    def test_parse_row_invalid_location_returns_none(self, timesheet_reader):
        """Test parsing row with invalid location returns None."""
        row = {
            "Date": "2023-06-15",
            "Project": "PROJ-001",
            "Location": "hybrid",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "Work",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        with patch("src.readers.timesheet_reader.logger") as mock_logger:
            entry = timesheet_reader._parse_row(row, freelancer_name)
            assert entry is None
            mock_logger.warning.assert_called()

    def test_parse_row_validation_error_returns_none(self, timesheet_reader):
        """Test parsing row with validation errors returns None."""
        row = {
            "Date": "2023-06-15",
            "Project": "",  # Empty project code triggers validation error
            "Location": "On-site",
            "Start Time": "09:00",
            "End Time": "17:00",
            "Topics worked on": "Work",
            "Break": "00:30",
            "Travel time": "00:00",
        }
        freelancer_name = "John Doe"

        with patch("src.readers.timesheet_reader.logger") as mock_logger:
            entry = timesheet_reader._parse_row(row, freelancer_name)
            assert entry is None
            mock_logger.warning.assert_called()

    def test_parse_row_unexpected_error_returns_none(self, timesheet_reader):
        """Test parsing row with unexpected errors returns None."""
        row = None  # This will cause unexpected error
        freelancer_name = "John Doe"

        with patch("src.readers.timesheet_reader.logger") as mock_logger:
            entry = timesheet_reader._parse_row(row, freelancer_name)
            assert entry is None
            mock_logger.warning.assert_called()

    def test_read_timesheet_service_error_raises_exception(
        self, timesheet_reader, mock_sheets_service
    ):
        """Test read_timesheet raises exception when service fails."""
        spreadsheet_id = "test-spreadsheet-id"

        # Mock service to raise exception
        mock_sheets_service.get_sheet_metadata.side_effect = Exception("Service error")

        with pytest.raises(Exception, match="Service error"):
            timesheet_reader.read_timesheet(spreadsheet_id)

    def test_time_to_minutes_with_empty_string(self, timesheet_reader):
        """Test converting empty string to minutes returns 0."""
        result = timesheet_reader._time_to_minutes("")
        assert result == 0

    def test_parse_time_with_whitespace(self, timesheet_reader):
        """Test parsing time with leading/trailing whitespace."""
        result = timesheet_reader._parse_time("  09:30  ")
        assert result == time(9, 30)
