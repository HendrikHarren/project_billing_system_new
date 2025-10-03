"""Unit tests for Timesheet model."""
from datetime import date, time

import pytest
from pydantic import ValidationError


class TestTimesheetModel:
    """Test Timesheet model creation and validation."""

    def test_create_valid_timesheet(self):
        """Test creating a timesheet with valid data."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        )

        assert entry.freelancer_name == "John Doe"
        assert entry.date == date(2023, 6, 15)
        assert entry.project_code == "PROJ-001"
        assert entry.start_time == time(9, 0)
        assert entry.end_time == time(17, 0)
        assert entry.break_minutes == 30
        assert entry.travel_time_minutes == 0
        assert entry.location == "remote"
        assert entry.notes is None

    def test_timesheet_with_notes(self):
        """Test creating a timesheet with optional notes."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="Jane Smith",
            date=date(2023, 6, 16),
            project_code="PROJ-002",
            start_time=time(10, 0),
            end_time=time(18, 30),
            break_minutes=60,
            travel_time_minutes=30,
            location="onsite",
            notes="Client meeting in the morning",
        )

        assert entry.notes == "Client meeting in the morning"

    def test_timesheet_onsite_location(self):
        """Test creating a timesheet with onsite location."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="Alice Brown",
            date=date(2023, 6, 17),
            project_code="PROJ-003",
            start_time=time(8, 0),
            end_time=time(16, 0),
            break_minutes=45,
            travel_time_minutes=120,
            location="onsite",
        )

        assert entry.location == "onsite"
        assert entry.travel_time_minutes == 120

    def test_invalid_location_raises_error(self):
        """Test that invalid location values raise validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="hybrid",  # Invalid - only 'remote' or 'onsite'
            )

        assert "location" in str(exc_info.value).lower()

    def test_negative_break_minutes_raises_error(self):
        """Test that negative break minutes raise validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_minutes=-30,  # Invalid - negative
                travel_time_minutes=0,
                location="remote",
            )

        assert "break_minutes" in str(exc_info.value).lower()

    def test_negative_travel_time_raises_error(self):
        """Test that negative travel time raises validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_minutes=30,
                travel_time_minutes=-60,  # Invalid - negative
                location="remote",
            )

        assert "travel_time_minutes" in str(exc_info.value).lower()

    def test_end_time_before_start_time_raises_error(self):
        """Test that end time before start time raises validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(17, 0),
                end_time=time(9, 0),  # Invalid - before start time (not overnight)
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )

        error_msg = str(exc_info.value).lower()
        assert "end_time" in error_msg or "start_time" in error_msg

    def test_overnight_shift_is_valid(self):
        """Test that overnight shifts (end_time < start_time) are valid with flag."""
        from src.models.timesheet import TimesheetEntry

        # For now, we'll require explicit overnight flag in future
        # But for MVP, let's allow it if end_time is close to midnight
        entry = TimesheetEntry(
            freelancer_name="Night Worker",
            date=date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=time(22, 0),
            end_time=time(6, 0),  # Next day
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )

        assert entry.start_time == time(22, 0)
        assert entry.end_time == time(6, 0)
        assert entry.is_overnight is True

    def test_break_exceeds_work_time_raises_error(self):
        """Test that break time exceeding work time raises validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(9, 0),
                end_time=time(17, 0),  # 8 hours = 480 minutes
                break_minutes=500,  # Invalid - exceeds work time
                travel_time_minutes=0,
                location="remote",
            )

        assert "break" in str(exc_info.value).lower()

    def test_empty_freelancer_name_raises_error(self):
        """Test that empty freelancer name raises validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="",  # Invalid - empty
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )

        assert "freelancer_name" in str(exc_info.value).lower()

    def test_empty_project_code_raises_error(self):
        """Test that empty project code raises validation error."""
        from src.models.timesheet import TimesheetEntry

        with pytest.raises(ValidationError) as exc_info:
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="",  # Invalid - empty
                start_time=time(9, 0),
                end_time=time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )

        assert "project_code" in str(exc_info.value).lower()

    def test_model_serialization(self):
        """Test that timesheet can be serialized to dict."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        )

        data = entry.model_dump()
        assert data["freelancer_name"] == "John Doe"
        assert data["date"] == date(2023, 6, 15)
        assert data["project_code"] == "PROJ-001"
        assert data["location"] == "remote"

    def test_model_deserialization(self):
        """Test that timesheet can be created from dict."""
        from src.models.timesheet import TimesheetEntry

        data = {
            "freelancer_name": "Jane Smith",
            "date": date(2023, 6, 16),
            "project_code": "PROJ-002",
            "start_time": time(10, 0),
            "end_time": time(18, 0),
            "break_minutes": 60,
            "travel_time_minutes": 30,
            "location": "onsite",
        }

        entry = TimesheetEntry.model_validate(data)
        assert entry.freelancer_name == "Jane Smith"
        assert entry.project_code == "PROJ-002"

    def test_date_string_parsing(self):
        """Test that date strings can be parsed automatically."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date="2023-06-15",  # String instead of date object
            project_code="PROJ-001",
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        )

        assert entry.date == date(2023, 6, 15)

    def test_time_string_parsing(self):
        """Test that time strings can be parsed automatically."""
        from src.models.timesheet import TimesheetEntry

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=date(2023, 6, 15),
            project_code="PROJ-001",
            start_time="09:00",  # String instead of time object
            end_time="17:00",  # String instead of time object
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        )

        assert entry.start_time == time(9, 0)
        assert entry.end_time == time(17, 0)
