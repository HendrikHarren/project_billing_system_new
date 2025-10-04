"""Tests for field-level validators."""

import datetime as dt
from decimal import Decimal

from src.validators.field_validators import FieldValidators
from src.validators.validation_report import ValidationReport


class TestDateValidation:
    """Tests for date validation."""

    def test_valid_date(self):
        """Test validation of valid date."""
        report = ValidationReport()
        date = dt.date(2023, 6, 15)

        FieldValidators.validate_date(date, "date", report)

        assert report.is_valid()
        assert report.error_count == 0

    def test_none_date(self):
        """Test validation of None date."""
        report = ValidationReport()

        FieldValidators.validate_date(None, "date", report)

        assert not report.is_valid()
        assert report.error_count == 1
        assert "date" in report.issues[0].field

    def test_future_date_warning(self):
        """Test warning for future dates."""
        report = ValidationReport()
        future_date = dt.date.today() + dt.timedelta(days=30)

        FieldValidators.validate_date(future_date, "date", report, allow_future=False)

        assert report.is_valid()  # Warning, not error
        assert report.warning_count == 1
        assert "future" in report.issues[0].message.lower()

    def test_very_old_date_warning(self):
        """Test warning for dates more than 2 years old."""
        report = ValidationReport()
        old_date = dt.date(2020, 1, 1)

        FieldValidators.validate_date(old_date, "date", report)

        assert report.is_valid()
        assert report.warning_count == 1
        assert "old" in report.issues[0].message.lower()

    def test_reasonable_date_range(self):
        """Test that recent dates don't trigger warnings."""
        report = ValidationReport()
        recent_date = dt.date.today() - dt.timedelta(days=30)

        FieldValidators.validate_date(recent_date, "date", report)

        assert report.is_valid()
        assert report.warning_count == 0


class TestTimeValidation:
    """Tests for time validation."""

    def test_valid_time(self):
        """Test validation of valid time."""
        report = ValidationReport()
        time = dt.time(9, 30)

        FieldValidators.validate_time(time, "start_time", report)

        assert report.is_valid()
        assert report.error_count == 0

    def test_none_time(self):
        """Test validation of None time."""
        report = ValidationReport()

        FieldValidators.validate_time(None, "start_time", report)

        assert not report.is_valid()
        assert report.error_count == 1

    def test_midnight_time(self):
        """Test validation of midnight (00:00)."""
        report = ValidationReport()
        time = dt.time(0, 0)

        FieldValidators.validate_time(time, "start_time", report)

        assert report.is_valid()

    def test_end_of_day_time(self):
        """Test validation of 23:59."""
        report = ValidationReport()
        time = dt.time(23, 59)

        FieldValidators.validate_time(time, "end_time", report)

        assert report.is_valid()


class TestStringValidation:
    """Tests for string validation."""

    def test_valid_string(self):
        """Test validation of valid non-empty string."""
        report = ValidationReport()

        FieldValidators.validate_non_empty_string("John Doe", "freelancer_name", report)

        assert report.is_valid()

    def test_empty_string(self):
        """Test validation of empty string."""
        report = ValidationReport()

        FieldValidators.validate_non_empty_string("", "project_code", report)

        assert not report.is_valid()
        assert report.error_count == 1
        assert "empty" in report.issues[0].message.lower()

    def test_whitespace_only_string(self):
        """Test validation of whitespace-only string."""
        report = ValidationReport()

        FieldValidators.validate_non_empty_string("   ", "project_code", report)

        assert not report.is_valid()
        assert report.error_count == 1

    def test_none_string(self):
        """Test validation of None string."""
        report = ValidationReport()

        FieldValidators.validate_non_empty_string(None, "freelancer_name", report)

        assert not report.is_valid()
        assert report.error_count == 1


class TestNumericValidation:
    """Tests for numeric validation."""

    def test_valid_positive_integer(self):
        """Test validation of positive integer."""
        report = ValidationReport()

        FieldValidators.validate_positive_number(100, "break_minutes", report)

        assert report.is_valid()

    def test_zero_value(self):
        """Test validation of zero (should be valid for non-negative)."""
        report = ValidationReport()

        FieldValidators.validate_non_negative_number(0, "break_minutes", report)

        assert report.is_valid()

    def test_zero_value_positive_required(self):
        """Test that zero fails for positive validation."""
        report = ValidationReport()

        FieldValidators.validate_positive_number(0, "hourly_rate", report)

        assert not report.is_valid()
        assert report.error_count == 1

    def test_negative_number(self):
        """Test validation of negative number."""
        report = ValidationReport()

        FieldValidators.validate_non_negative_number(-10, "break_minutes", report)

        assert not report.is_valid()
        assert report.error_count == 1
        assert "negative" in report.issues[0].message.lower()

    def test_none_number(self):
        """Test validation of None number."""
        report = ValidationReport()

        FieldValidators.validate_positive_number(None, "hourly_rate", report)

        assert not report.is_valid()
        assert report.error_count == 1

    def test_decimal_validation(self):
        """Test validation of Decimal numbers."""
        report = ValidationReport()

        FieldValidators.validate_positive_number(
            Decimal("85.50"), "hourly_rate", report
        )

        assert report.is_valid()

    def test_range_validation_within_range(self):
        """Test validation of number within range."""
        report = ValidationReport()

        FieldValidators.validate_number_range(
            50, "percentage", report, min_val=0, max_val=100
        )

        assert report.is_valid()

    def test_range_validation_below_minimum(self):
        """Test validation of number below minimum."""
        report = ValidationReport()

        FieldValidators.validate_number_range(
            -10, "percentage", report, min_val=0, max_val=100
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_range_validation_above_maximum(self):
        """Test validation of number above maximum."""
        report = ValidationReport()

        FieldValidators.validate_number_range(
            150, "percentage", report, min_val=0, max_val=100
        )

        assert not report.is_valid()
        assert report.error_count == 1

    def test_range_validation_at_boundaries(self):
        """Test validation at exact min/max boundaries."""
        report = ValidationReport()

        FieldValidators.validate_number_range(
            0, "percentage", report, min_val=0, max_val=100
        )
        assert report.is_valid()

        report2 = ValidationReport()
        FieldValidators.validate_number_range(
            100, "percentage", report2, min_val=0, max_val=100
        )
        assert report2.is_valid()


class TestLocationValidation:
    """Tests for location validation."""

    def test_valid_remote_location(self):
        """Test validation of 'remote' location."""
        report = ValidationReport()

        FieldValidators.validate_location("remote", "location", report)

        assert report.is_valid()

    def test_valid_onsite_location(self):
        """Test validation of 'onsite' location."""
        report = ValidationReport()

        FieldValidators.validate_location("onsite", "location", report)

        assert report.is_valid()

    def test_invalid_location(self):
        """Test validation of invalid location."""
        report = ValidationReport()

        FieldValidators.validate_location("office", "location", report)

        assert not report.is_valid()
        assert report.error_count == 1
        assert "remote" in report.issues[0].message.lower()
        assert "onsite" in report.issues[0].message.lower()

    def test_none_location(self):
        """Test validation of None location."""
        report = ValidationReport()

        FieldValidators.validate_location(None, "location", report)

        assert not report.is_valid()

    def test_case_sensitivity(self):
        """Test that location validation is case-sensitive."""
        report = ValidationReport()

        FieldValidators.validate_location("Remote", "location", report)

        assert not report.is_valid()
        assert report.error_count == 1


class TestProjectCodeValidation:
    """Tests for project code validation."""

    def test_valid_project_code(self):
        """Test validation of valid project code."""
        report = ValidationReport()

        FieldValidators.validate_project_code("PROJ-001", "project_code", report)

        assert report.is_valid()

    def test_empty_project_code(self):
        """Test validation of empty project code."""
        report = ValidationReport()

        FieldValidators.validate_project_code("", "project_code", report)

        assert not report.is_valid()

    def test_whitespace_project_code(self):
        """Test validation of whitespace project code."""
        report = ValidationReport()

        FieldValidators.validate_project_code("  ", "project_code", report)

        assert not report.is_valid()

    def test_project_code_with_special_characters(self):
        """Test that project codes with various formats are valid."""
        report = ValidationReport()

        # Test various valid formats
        codes = ["PROJ-001", "ABC_123", "Project.2023", "P123"]
        for code in codes:
            report = ValidationReport()
            FieldValidators.validate_project_code(code, "project_code", report)
            assert report.is_valid(), f"Code '{code}' should be valid"
