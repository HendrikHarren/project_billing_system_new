"""Tests for the main validator orchestrator."""

import datetime as dt
from decimal import Decimal

from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry
from src.validators.validator import TimesheetValidator


class TestTimesheetValidator:
    """Tests for TimesheetValidator orchestrator."""

    def test_validate_single_entry_valid(self):
        """Test validation of a single valid timesheet entry."""
        validator = TimesheetValidator()

        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=60,
            travel_time_minutes=30,
            location="remote",
        )

        report = validator.validate_entry(entry)

        assert report.is_valid()
        assert report.error_count == 0

    def test_validate_single_entry_with_errors(self):
        """Test validation catches errors in timesheet entry."""
        validator = TimesheetValidator()

        # Use model_construct to bypass Pydantic validation
        entry = TimesheetEntry.model_construct(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=500,  # Invalid - exceeds work time
            travel_time_minutes=30,
            location="remote",
            is_overnight=False,
        )

        report = validator.validate_entry(entry)

        assert not report.is_valid()
        assert report.error_count > 0

    def test_validate_multiple_entries(self):
        """Test validation of multiple timesheet entries."""
        validator = TimesheetValidator()

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=60,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=dt.date(2023, 6, 16),
                project_code="PROJ-002",
                start_time=dt.time(10, 0),
                end_time=dt.time(18, 0),
                break_minutes=45,
                travel_time_minutes=120,
                location="onsite",
            ),
        ]

        report = validator.validate_entries(entries)

        assert report.is_valid()
        assert report.error_count == 0

    def test_validate_multiple_entries_with_some_errors(self):
        """Test validation of multiple entries where some have errors."""
        validator = TimesheetValidator()

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=60,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry.model_construct(
                freelancer_name="Jane Smith",
                date=dt.date(2023, 6, 16),
                project_code="PROJ-002",
                start_time=dt.time(10, 0),
                end_time=dt.time(18, 0),
                break_minutes=600,  # Invalid
                travel_time_minutes=120,
                location="onsite",
                is_overnight=False,
            ),
        ]

        report = validator.validate_entries(entries)

        assert not report.is_valid()
        assert report.error_count > 0

    def test_validate_project_terms_valid(self):
        """Test validation of valid project terms."""
        validator = TimesheetValidator()

        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        report = validator.validate_terms(terms)

        assert report.is_valid()

    def test_validate_project_terms_with_errors(self):
        """Test validation catches errors in project terms."""
        validator = TimesheetValidator()

        # Use model_construct to bypass Pydantic validation
        terms = ProjectTerms.model_construct(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("90.00"),  # Invalid - exceeds rate
        )

        report = validator.validate_terms(terms)

        assert not report.is_valid()

    def test_validate_empty_list(self):
        """Test validation of empty list returns valid report."""
        validator = TimesheetValidator()

        report = validator.validate_entries([])

        assert report.is_valid()
        assert len(report.issues) == 0

    def test_validation_includes_context(self):
        """Test that validation report includes context information."""
        validator = TimesheetValidator()

        entry = TimesheetEntry.model_construct(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=500,
            travel_time_minutes=0,
            location="remote",
            is_overnight=False,
        )

        report = validator.validate_entry(entry, row_number=5)

        assert not report.is_valid()
        # Check that context includes row number
        assert any(
            issue.context and issue.context.get("row") == 5 for issue in report.issues
        )

    def test_field_only_validation(self):
        """Test validation with fields only (skip business rules)."""
        validator = TimesheetValidator()

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

        report = validator.validate_entry(entry, validate_business_rules=False)

        assert report.is_valid()

    def test_warnings_dont_invalidate_report(self):
        """Test that warnings don't make the report invalid."""
        validator = TimesheetValidator()

        # Create entry that triggers warnings but not errors
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2020, 1, 1),  # Old date - triggers warning
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=60,
            travel_time_minutes=0,
            location="remote",
        )

        report = validator.validate_entry(entry)

        assert report.is_valid()  # Warnings don't invalidate
        assert report.warning_count > 0


class TestValidationModes:
    """Tests for different validation modes."""

    def test_quick_validation_mode(self):
        """Test quick validation (fields only, no business rules)."""
        validator = TimesheetValidator()

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

        report = validator.validate_entry(entry, validate_business_rules=False)

        assert report.is_valid()

    def test_full_validation_mode(self):
        """Test full validation (fields + business rules)."""
        validator = TimesheetValidator()

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

        report = validator.validate_entry(entry, validate_business_rules=True)

        assert report.is_valid()
