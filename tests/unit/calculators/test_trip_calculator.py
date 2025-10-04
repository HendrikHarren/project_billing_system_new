"""Unit tests for trip calculator."""

import datetime as dt
from datetime import date

from src.calculators.trip_calculator import calculate_trips
from src.models.timesheet import TimesheetEntry


class TestCalculateTrips:
    """Test calculate_trips function for grouping consecutive on-site days."""

    def test_empty_list_returns_empty(self):
        """Test that empty input returns empty list."""
        result = calculate_trips([])
        assert result == []

    def test_single_day_trip(self):
        """Test single on-site day creates one-day trip."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            )
        ]

        result = calculate_trips(entries)

        assert len(result) == 1
        assert result[0].freelancer_name == "John Doe"
        assert result[0].project_code == "PROJ-001"
        assert result[0].location == "onsite"
        assert result[0].start_date == date(2023, 6, 15)
        assert result[0].end_date == date(2023, 6, 15)
        assert result[0].duration_days == 1

    def test_consecutive_days_single_trip(self):
        """Test consecutive on-site days are grouped into single trip."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 14),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 1
        assert result[0].start_date == date(2023, 6, 12)
        assert result[0].end_date == date(2023, 6, 14)
        assert result[0].duration_days == 3

    def test_gap_creates_separate_trips(self):
        """Test that gap > 1 day creates separate trips."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            # Gap of 2 days
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 16),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 17),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 2
        # First trip
        assert result[0].start_date == date(2023, 6, 12)
        assert result[0].end_date == date(2023, 6, 13)
        assert result[0].duration_days == 2
        # Second trip
        assert result[1].start_date == date(2023, 6, 16)
        assert result[1].end_date == date(2023, 6, 17)
        assert result[1].duration_days == 2

    def test_remote_entries_ignored(self):
        """Test that remote entries are filtered out."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 14),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 1
        assert result[0].start_date == date(2023, 6, 13)
        assert result[0].end_date == date(2023, 6, 13)
        assert result[0].duration_days == 1

    def test_different_projects_separate_consecutive_days(self):
        """Test that different projects on consecutive days create separate trips."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 2
        assert result[0].project_code == "PROJ-001"
        assert result[1].project_code == "PROJ-002"

    def test_different_projects_separate_trips(self):
        """Test that different projects create separate trips."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 2
        assert result[0].project_code == "PROJ-001"
        assert result[1].project_code == "PROJ-002"

    def test_multiple_freelancers_isolated(self):
        """Test that different freelancers are tracked separately."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 2
        # Find trips by freelancer
        john_trips = [t for t in result if t.freelancer_name == "John Doe"]
        jane_trips = [t for t in result if t.freelancer_name == "Jane Smith"]

        assert len(john_trips) == 1
        assert len(jane_trips) == 1
        assert john_trips[0].duration_days == 2
        assert jane_trips[0].duration_days == 2

    def test_unsorted_entries_handled_correctly(self):
        """Test that unsorted entries are sorted before processing."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 14),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 1
        assert result[0].start_date == date(2023, 6, 12)
        assert result[0].end_date == date(2023, 6, 14)
        assert result[0].duration_days == 3

    def test_same_day_multiple_entries_single_trip(self):
        """Test that multiple entries on same day are counted once."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(12, 0),
                break_minutes=0,
                travel_time_minutes=60,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(13, 0),
                end_time=dt.time(17, 0),
                break_minutes=0,
                travel_time_minutes=0,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 1
        assert result[0].start_date == date(2023, 6, 12)
        assert result[0].end_date == date(2023, 6, 12)
        assert result[0].duration_days == 1

    def test_complex_scenario_matching_notebook(self):
        """Test complex scenario with multiple freelancers, projects, and gaps."""
        entries = [
            # John - PROJ-001: Trip 1 (June 5-7)
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 5),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=120,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 6),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 7),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=120,
                location="onsite",
            ),
            # John - Remote work (should be ignored)
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 8),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            # John - PROJ-001: Trip 2 (June 12-13)
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 12),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=120,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=date(2023, 6, 13),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=120,
                location="onsite",
            ),
            # Jane - PROJ-002: Trip 3 (June 5-6)
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=date(2023, 6, 5),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=90,
                location="onsite",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=date(2023, 6, 6),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=90,
                location="onsite",
            ),
        ]

        result = calculate_trips(entries)

        assert len(result) == 3

        # John's first trip
        john_trip1 = [
            t
            for t in result
            if t.freelancer_name == "John Doe" and t.start_date == date(2023, 6, 5)
        ][0]
        assert john_trip1.end_date == date(2023, 6, 7)
        assert john_trip1.duration_days == 3
        assert john_trip1.location == "onsite"

        # John's second trip
        john_trip2 = [
            t
            for t in result
            if t.freelancer_name == "John Doe" and t.start_date == date(2023, 6, 12)
        ][0]
        assert john_trip2.end_date == date(2023, 6, 13)
        assert john_trip2.duration_days == 2
        assert john_trip2.location == "onsite"

        # Jane's trip
        jane_trip = [t for t in result if t.freelancer_name == "Jane Smith"][0]
        assert jane_trip.start_date == date(2023, 6, 5)
        assert jane_trip.end_date == date(2023, 6, 6)
        assert jane_trip.duration_days == 2
        assert jane_trip.location == "onsite"
        assert jane_trip.project_code == "PROJ-002"
