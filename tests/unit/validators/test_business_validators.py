"""Tests for business rule validators."""

import datetime as dt
from decimal import Decimal

from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry
from src.validators.business_validators import BusinessRuleValidators
from src.validators.validation_report import ValidationReport


class TestTimeRangeValidation:
    """Tests for time range business rules."""

    def test_valid_normal_shift(self):
        """Test validation of normal shift (start < end)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_time_range(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            is_overnight=False,
            field_prefix="",
            report=report,
        )

        assert report.is_valid()

    def test_invalid_normal_shift(self):
        """Test validation when end time is before start time for normal shift."""
        report = ValidationReport()

        BusinessRuleValidators.validate_time_range(
            start_time=dt.time(17, 0),
            end_time=dt.time(9, 0),
            is_overnight=False,
            field_prefix="",
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1
        assert "end_time" in report.issues[0].field

    def test_valid_overnight_shift(self):
        """Test validation of overnight shift."""
        report = ValidationReport()

        BusinessRuleValidators.validate_time_range(
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            is_overnight=True,
            field_prefix="",
            report=report,
        )

        assert report.is_valid()

    def test_overnight_flag_mismatch_warning(self):
        """Test warning when overnight flag doesn't match time order."""
        report = ValidationReport()

        # Times suggest overnight but flag is False
        BusinessRuleValidators.validate_time_range(
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            is_overnight=False,
            field_prefix="",
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_same_start_and_end_time(self):
        """Test validation when start and end times are the same."""
        report = ValidationReport()

        BusinessRuleValidators.validate_time_range(
            start_time=dt.time(9, 0),
            end_time=dt.time(9, 0),
            is_overnight=False,
            field_prefix="",
            report=report,
        )

        assert not report.is_valid()


class TestBreakTimeValidation:
    """Tests for break time business rules."""

    def test_valid_break_time(self):
        """Test validation of valid break time (less than work time)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=60,
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()

    def test_break_equals_work_time(self):
        """Test error when break time equals work time."""
        report = ValidationReport()

        # 8 hours = 480 minutes
        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=480,
            is_overnight=False,
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_break_exceeds_work_time(self):
        """Test error when break time exceeds work time."""
        report = ValidationReport()

        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=600,  # 10 hours break for 8 hour work day
            is_overnight=False,
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_zero_break_time(self):
        """Test validation with zero break time."""
        report = ValidationReport()

        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()

    def test_overnight_shift_break_validation(self):
        """Test break validation for overnight shifts."""
        report = ValidationReport()

        # Overnight shift: 22:00 to 06:00 = 8 hours
        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=60,
            is_overnight=True,
            report=report,
        )

        assert report.is_valid()

    def test_unusually_long_break_warning(self):
        """Test warning for unusually long breaks."""
        report = ValidationReport()

        # 4.5 hour break in 8 hour shift (> 50%)
        BusinessRuleValidators.validate_break_time(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=250,  # > 50% of 480 minutes
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()  # Not an error
        assert report.warning_count == 1
        assert "unusually long" in report.issues[0].message.lower()


class TestProfitMarginValidation:
    """Tests for profit margin business rules."""

    def test_valid_profit_margin(self):
        """Test validation with valid profit margin (cost < rate)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_profit_margin(
            cost_per_hour=Decimal("60.00"),
            hourly_rate=Decimal("85.00"),
            report=report,
        )

        assert report.is_valid()

    def test_cost_equals_rate(self):
        """Test error when cost equals rate (no profit)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_profit_margin(
            cost_per_hour=Decimal("85.00"),
            hourly_rate=Decimal("85.00"),
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1
        assert "profit" in report.issues[0].message.lower()

    def test_cost_exceeds_rate(self):
        """Test error when cost exceeds rate (negative profit)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_profit_margin(
            cost_per_hour=Decimal("100.00"),
            hourly_rate=Decimal("85.00"),
            report=report,
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_low_profit_margin_warning(self):
        """Test warning when profit margin is very low (< 10%)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_profit_margin(
            cost_per_hour=Decimal("80.00"),
            hourly_rate=Decimal("85.00"),  # Only 5.88% margin
            report=report,
        )

        assert report.is_valid()  # Not an error
        assert report.warning_count == 1
        assert "low profit margin" in report.issues[0].message.lower()


class TestTimesheetEntryValidation:
    """Tests for complete timesheet entry validation."""

    def test_valid_timesheet_entry(self):
        """Test validation of a complete valid timesheet entry."""
        report = ValidationReport()

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=60,
            travel_time_minutes=0,
            location="remote",
        )

        BusinessRuleValidators.validate_timesheet_entry(entry, report)

        assert report.is_valid()

    def test_timesheet_entry_with_invalid_break(self):
        """Test validation catches invalid break time."""
        report = ValidationReport()

        # Use model_construct to bypass Pydantic validation for testing
        entry = TimesheetEntry.model_construct(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=500,  # Exceeds work time
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )

        BusinessRuleValidators.validate_timesheet_entry(entry, report)

        assert not report.is_valid()
        assert report.error_count >= 1

    def test_timesheet_entry_overnight_validation(self):
        """Test validation of overnight timesheet entry."""
        report = ValidationReport()

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="onsite",
            is_overnight=True,
        )

        BusinessRuleValidators.validate_timesheet_entry(entry, report)

        assert report.is_valid()


class TestProjectTermsValidation:
    """Tests for project terms validation."""

    def test_valid_project_terms(self):
        """Test validation of valid project terms."""
        report = ValidationReport()

        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        BusinessRuleValidators.validate_project_terms(terms, report)

        assert report.is_valid()

    def test_project_terms_with_invalid_profit(self):
        """Test validation catches invalid profit margin."""
        report = ValidationReport()

        # Use model_construct to bypass Pydantic validation for testing
        terms = ProjectTerms.model_construct(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("90.00"),  # Exceeds rate
        )

        BusinessRuleValidators.validate_project_terms(terms, report)

        assert not report.is_valid()

    def test_project_terms_percentage_validation(self):
        """Test that percentages are within valid range."""
        report = ValidationReport()

        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        BusinessRuleValidators.validate_project_terms(terms, report)

        assert report.is_valid()
        # Percentages are validated by Pydantic model constraints


class TestWorkDurationValidation:
    """Tests for work duration validation."""

    def test_reasonable_work_duration(self):
        """Test that reasonable work durations pass validation."""
        report = ValidationReport()

        BusinessRuleValidators.validate_work_duration(
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()

    def test_very_long_shift_warning(self):
        """Test warning for unusually long shifts (> 12 hours)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_work_duration(
            start_time=dt.time(8, 0),
            end_time=dt.time(23, 0),  # 15 hours
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()  # Warning, not error
        assert report.warning_count == 1
        assert "long" in report.issues[0].message.lower()

    def test_very_short_shift_warning(self):
        """Test warning for unusually short shifts (< 2 hours)."""
        report = ValidationReport()

        BusinessRuleValidators.validate_work_duration(
            start_time=dt.time(9, 0),
            end_time=dt.time(10, 0),  # 1 hour
            is_overnight=False,
            report=report,
        )

        assert report.is_valid()  # Warning, not error
        assert report.warning_count == 1
        assert "short" in report.issues[0].message.lower()
