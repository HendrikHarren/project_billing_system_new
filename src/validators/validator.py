"""Main validator orchestrator for timesheet validation.

This module provides the main TimesheetValidator class that coordinates
field validation and business rule validation.
"""

from typing import List, Optional

from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry
from src.validators.business_validators import BusinessRuleValidators
from src.validators.field_validators import FieldValidators
from src.validators.validation_report import ValidationReport


class TimesheetValidator:
    """Main validator for timesheet entries and project terms.

    This class orchestrates field-level and business rule validation,
    providing a unified interface for validating timesheet data.

    Example:
        >>> validator = TimesheetValidator()
        >>> entry = TimesheetEntry(...)
        >>> report = validator.validate_entry(entry)
        >>> if not report.is_valid():
        ...     print(report.format())
    """

    def __init__(self) -> None:
        """Initialize the validator."""
        pass

    def validate_entry(
        self,
        entry: TimesheetEntry,
        validate_business_rules: bool = True,
        row_number: Optional[int] = None,
    ) -> ValidationReport:
        """Validate a single timesheet entry.

        Args:
            entry: The timesheet entry to validate
            validate_business_rules: Whether to validate business rules (default: True)
            row_number: Optional row number for context in error messages

        Returns:
            ValidationReport with any issues found

        Example:
            >>> validator = TimesheetValidator()
            >>> entry = TimesheetEntry(...)
            >>> report = validator.validate_entry(entry, row_number=5)
        """
        report = ValidationReport()
        context = {"row": row_number} if row_number is not None else None

        # Validate fields
        self._validate_entry_fields(entry, report, context)

        # Validate business rules if requested
        if validate_business_rules:
            self._validate_entry_business_rules(entry, report, context)

        return report

    def validate_entries(
        self,
        entries: List[TimesheetEntry],
        validate_business_rules: bool = True,
    ) -> ValidationReport:
        """Validate multiple timesheet entries.

        Args:
            entries: List of timesheet entries to validate
            validate_business_rules: Whether to validate business rules (default: True)

        Returns:
            ValidationReport with all issues found across all entries

        Example:
            >>> validator = TimesheetValidator()
            >>> entries = [entry1, entry2, entry3]
            >>> report = validator.validate_entries(entries)
        """
        combined_report = ValidationReport()

        for idx, entry in enumerate(entries, start=1):
            entry_report = self.validate_entry(
                entry,
                validate_business_rules=validate_business_rules,
                row_number=idx,
            )
            combined_report.merge(entry_report)

        return combined_report

    def validate_terms(
        self,
        terms: ProjectTerms,
        validate_business_rules: bool = True,
    ) -> ValidationReport:
        """Validate project terms.

        Args:
            terms: The project terms to validate
            validate_business_rules: Whether to validate business rules (default: True)

        Returns:
            ValidationReport with any issues found

        Example:
            >>> validator = TimesheetValidator()
            >>> terms = ProjectTerms(...)
            >>> report = validator.validate_terms(terms)
        """
        report = ValidationReport()

        # Validate fields
        self._validate_terms_fields(terms, report)

        # Validate business rules if requested
        if validate_business_rules:
            BusinessRuleValidators.validate_project_terms(terms, report)

        return report

    def _validate_entry_fields(
        self,
        entry: TimesheetEntry,
        report: ValidationReport,
        context: Optional[dict] = None,
    ) -> None:
        """Validate individual fields of a timesheet entry.

        Args:
            entry: The timesheet entry to validate
            report: ValidationReport to collect issues
            context: Optional context for error messages
        """
        # Validate date
        FieldValidators.validate_date(
            entry.date,
            "date",
            report,
            allow_future=True,
        )

        # Validate times
        FieldValidators.validate_time(entry.start_time, "start_time", report)
        FieldValidators.validate_time(entry.end_time, "end_time", report)

        # Validate strings
        FieldValidators.validate_non_empty_string(
            entry.freelancer_name, "freelancer_name", report
        )
        FieldValidators.validate_project_code(
            entry.project_code, "project_code", report
        )

        # Validate numbers
        FieldValidators.validate_non_negative_number(
            entry.break_minutes, "break_minutes", report
        )
        FieldValidators.validate_non_negative_number(
            entry.travel_time_minutes, "travel_time_minutes", report
        )

        # Validate location
        FieldValidators.validate_location(entry.location, "location", report)

        # Add context to all issues if provided
        if context:
            for issue in report.issues:
                if issue.context is None:
                    issue.context = context.copy()
                else:
                    issue.context.update(context)

    def _validate_entry_business_rules(
        self,
        entry: TimesheetEntry,
        report: ValidationReport,
        context: Optional[dict] = None,
    ) -> None:
        """Validate business rules for a timesheet entry.

        Args:
            entry: The timesheet entry to validate
            report: ValidationReport to collect issues
            context: Optional context for error messages
        """
        # Add freelancer and project to context
        business_context = {
            "freelancer": entry.freelancer_name,
            "project": entry.project_code,
        }
        if context:
            business_context.update(context)

        # Create a sub-report for business rules
        business_report = ValidationReport()
        BusinessRuleValidators.validate_timesheet_entry(entry, business_report)

        # Add context to business rule issues
        for issue in business_report.issues:
            if issue.context is None:
                issue.context = business_context.copy()
            else:
                issue.context.update(business_context)

        # Merge business rule report
        report.merge(business_report)

    def _validate_terms_fields(
        self,
        terms: ProjectTerms,
        report: ValidationReport,
    ) -> None:
        """Validate individual fields of project terms.

        Args:
            terms: The project terms to validate
            report: ValidationReport to collect issues
        """
        # Validate strings
        FieldValidators.validate_non_empty_string(
            terms.freelancer_name, "freelancer_name", report
        )
        FieldValidators.validate_project_code(
            terms.project_code, "project_code", report
        )

        # Validate rates and costs
        FieldValidators.validate_positive_number(
            terms.hourly_rate, "hourly_rate", report
        )
        FieldValidators.validate_non_negative_number(
            terms.cost_per_hour, "cost_per_hour", report
        )

        # Validate percentages (0-100)
        FieldValidators.validate_number_range(
            terms.travel_surcharge_percentage,
            "travel_surcharge_percentage",
            report,
            min_val=0,
            max_val=100,
        )
        FieldValidators.validate_number_range(
            terms.travel_time_percentage,
            "travel_time_percentage",
            report,
            min_val=0,
            max_val=100,
        )
