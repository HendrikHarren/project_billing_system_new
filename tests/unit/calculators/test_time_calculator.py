"""Unit tests for time calculation engine.

This module tests the business logic for calculating billable hours,
amounts, and travel surcharges.
"""

import datetime as dt
from decimal import Decimal

from src.calculators.time_calculator import (
    calculate_billable_amount,
    calculate_billable_hours,
    calculate_travel_surcharge,
    calculate_work_duration,
)
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


class TestCalculateWorkDuration:
    """Test work duration calculation."""

    def test_normal_shift(self):
        """Test calculating duration for a normal shift."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        result = calculate_work_duration(entry)
        assert result == dt.timedelta(hours=8)

    def test_overnight_shift(self):
        """Test calculating duration for an overnight shift."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )
        result = calculate_work_duration(entry)
        assert result == dt.timedelta(hours=8)

    def test_shift_ending_at_midnight(self):
        """Test shift ending exactly at midnight (00:00 = next day)."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(22, 0),
            end_time=dt.time(0, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )
        result = calculate_work_duration(entry)
        assert result == dt.timedelta(hours=2)


class TestCalculateBillableHours:
    """Test billable hours calculation with breaks and travel time."""

    def test_basic_calculation_no_breaks_no_travel(self):
        """Test basic 8-hour shift with no breaks or travel."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_hours(entry, terms)
        assert result.total_hours == Decimal("8.00")
        assert result.work_hours == Decimal("8.00")
        assert result.break_hours == Decimal("0.00")
        assert result.travel_hours == Decimal("0.00")

    def test_with_break(self):
        """Test 8-hour shift with 30-minute break."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_hours(entry, terms)
        assert result.total_hours == Decimal("7.50")
        assert result.work_hours == Decimal("8.00")
        assert result.break_hours == Decimal("0.50")

    def test_with_travel_time_50_percent(self):
        """Test shift with 60 minutes travel at 50% billable."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=60,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_hours(entry, terms)
        # 8 hours work - 0 break + (0.5 * 1 hour travel) = 8.5 hours
        assert result.total_hours == Decimal("8.50")
        assert result.work_hours == Decimal("8.00")
        assert result.travel_hours == Decimal("0.50")

    def test_full_scenario(self):
        """Test complete scenario: 8h work, 30min break, 60min travel at 50%."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=60,
            location="onsite",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_hours(entry, terms)
        # 8 - 0.5 + (0.5 * 1) = 8.0 hours
        assert result.total_hours == Decimal("8.00")
        assert result.work_hours == Decimal("8.00")
        assert result.break_hours == Decimal("0.50")
        assert result.travel_hours == Decimal("0.50")

    def test_overnight_shift_with_break(self):
        """Test overnight shift with breaks."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_hours(entry, terms)
        # 8 hours - 0.5 break = 7.5 hours
        assert result.total_hours == Decimal("7.50")


class TestCalculateBillableAmount:
    """Test billable amount calculation."""

    def test_basic_calculation(self):
        """Test basic amount calculation: 8 hours at 85/hour."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_amount(entry, terms)
        assert result == Decimal("680.00")

    def test_with_break(self):
        """Test amount with break: 7.5 hours at 85/hour."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_amount(entry, terms)
        assert result == Decimal("637.50")

    def test_with_travel(self):
        """Test amount with travel: (8 + 0.5) hours at 85/hour."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=60,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_billable_amount(entry, terms)
        # 8.5 hours * 85 = 722.50
        assert result == Decimal("722.50")


class TestCalculateTravelSurcharge:
    """Test travel surcharge calculation for on-site work."""

    def test_no_surcharge_for_remote(self):
        """Test that remote work has no travel surcharge."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_travel_surcharge(entry, terms)
        assert result == Decimal("0.00")

    def test_surcharge_for_onsite(self):
        """Test travel surcharge for on-site work."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=60,
            location="onsite",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_travel_surcharge(entry, terms)
        # Billable hours = 8 - 0.5 + 0.5 = 8.0 hours
        # Surcharge = 8.0 * 85 * 0.15 = 102.00
        assert result == Decimal("102.00")

    def test_surcharge_with_zero_percentage(self):
        """Test that 0% surcharge returns 0."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="onsite",
            is_overnight=False,
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("0.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
        result = calculate_travel_surcharge(entry, terms)
        assert result == Decimal("0.00")
