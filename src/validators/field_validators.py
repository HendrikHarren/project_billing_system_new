"""Field-level validators for timesheet data.

This module provides validators for individual fields such as dates,
times, strings, numbers, and locations.
"""

import datetime as dt
from decimal import Decimal
from typing import Optional, Union

from src.validators.validation_report import ValidationReport


class FieldValidators:
    """Collection of field-level validation methods.

    This class provides static methods for validating individual fields
    in timesheet entries, project terms, and other data models.
    """

    @staticmethod
    def validate_date(
        value: Optional[dt.date],
        field_name: str,
        report: ValidationReport,
        allow_future: bool = True,
    ) -> None:
        """Validate a date field.

        Args:
            value: The date value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
            allow_future: Whether to allow future dates (default: True)
        """
        if value is None:
            report.add_error(field_name, "Date is required", None)
            return

        # Check for future dates
        if not allow_future and value > dt.date.today():
            report.add_warning(
                field_name,
                "Date is in the future",
                value,
            )

        # Warn if date is very old (more than 2 years)
        two_years_ago = dt.date.today() - dt.timedelta(days=730)
        if value < two_years_ago:
            report.add_warning(
                field_name,
                "Date is more than 2 years old",
                value,
            )

    @staticmethod
    def validate_time(
        value: Optional[dt.time],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate a time field.

        Args:
            value: The time value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        if value is None:
            report.add_error(field_name, "Time is required", None)
            return

        # Time values are already validated by dt.time constructor
        # Just ensure it's a valid time object
        if not isinstance(value, dt.time):
            report.add_error(
                field_name,
                "Invalid time format",
                value,
            )

    @staticmethod
    def validate_non_empty_string(
        value: Optional[str],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate that a string is not empty or whitespace.

        Args:
            value: The string value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        if value is None:
            report.add_error(field_name, "Value is required", None)
            return

        if not isinstance(value, str):
            report.add_error(
                field_name,
                f"Expected string, got {type(value).__name__}",
                value,
            )
            return

        if not value.strip():
            report.add_error(
                field_name,
                "Value cannot be empty or whitespace",
                value,
            )

    @staticmethod
    def validate_positive_number(
        value: Optional[Union[int, float, Decimal]],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate that a number is positive (> 0).

        Args:
            value: The numeric value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        if value is None:
            report.add_error(field_name, "Value is required", None)
            return

        if not isinstance(value, (int, float, Decimal)):
            report.add_error(
                field_name,
                f"Expected number, got {type(value).__name__}",
                value,
            )
            return

        if value <= 0:
            report.add_error(
                field_name,
                "Value must be positive (greater than 0)",
                value,
            )

    @staticmethod
    def validate_non_negative_number(
        value: Optional[Union[int, float, Decimal]],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate that a number is non-negative (>= 0).

        Args:
            value: The numeric value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        if value is None:
            report.add_error(field_name, "Value is required", None)
            return

        if not isinstance(value, (int, float, Decimal)):
            report.add_error(
                field_name,
                f"Expected number, got {type(value).__name__}",
                value,
            )
            return

        if value < 0:
            report.add_error(
                field_name,
                "Value cannot be negative",
                value,
            )

    @staticmethod
    def validate_number_range(
        value: Optional[Union[int, float, Decimal]],
        field_name: str,
        report: ValidationReport,
        min_val: Optional[Union[int, float, Decimal]] = None,
        max_val: Optional[Union[int, float, Decimal]] = None,
    ) -> None:
        """Validate that a number is within a specified range.

        Args:
            value: The numeric value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
        """
        if value is None:
            report.add_error(field_name, "Value is required", None)
            return

        if not isinstance(value, (int, float, Decimal)):
            report.add_error(
                field_name,
                f"Expected number, got {type(value).__name__}",
                value,
            )
            return

        if min_val is not None and value < min_val:
            report.add_error(
                field_name,
                f"Value must be at least {min_val}",
                value,
            )

        if max_val is not None and value > max_val:
            report.add_error(
                field_name,
                f"Value must be at most {max_val}",
                value,
            )

    @staticmethod
    def validate_location(
        value: Optional[str],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate that location is either 'remote' or 'onsite'.

        Args:
            value: The location value to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        if value is None:
            report.add_error(field_name, "Location is required", None)
            return

        if value not in ("remote", "onsite"):
            report.add_error(
                field_name,
                "Location must be either 'remote' or 'onsite'",
                value,
            )

    @staticmethod
    def validate_project_code(
        value: Optional[str],
        field_name: str,
        report: ValidationReport,
    ) -> None:
        """Validate project code format.

        Project codes must be non-empty strings.

        Args:
            value: The project code to validate
            field_name: Name of the field being validated
            report: ValidationReport to collect issues
        """
        # Project codes are just non-empty strings
        FieldValidators.validate_non_empty_string(value, field_name, report)
