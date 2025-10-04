"""Business rule validators for timesheet data.

This module provides validators for business logic rules such as
time ranges, break times, profit margins, and other domain-specific validations.
"""

import datetime as dt
from decimal import Decimal

from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry
from src.validators.validation_report import ValidationReport


class BusinessRuleValidators:
    """Collection of business rule validation methods.

    This class provides static methods for validating business logic
    constraints in timesheet entries and project terms.
    """

    @staticmethod
    def validate_time_range(
        start_time: dt.time,
        end_time: dt.time,
        is_overnight: bool,
        field_prefix: str,
        report: ValidationReport,
    ) -> None:
        """Validate that time range is logical.

        Args:
            start_time: Work start time
            end_time: Work end time
            is_overnight: Whether shift spans midnight
            field_prefix: Prefix for field names in error messages
            report: ValidationReport to collect issues
        """
        if not is_overnight:
            # For normal shifts, end must be after start
            if end_time <= start_time:
                report.add_error(
                    f"{field_prefix}end_time",
                    f"End time ({end_time}) must be after start time ({start_time}) "
                    "for non-overnight shifts",
                    end_time,
                )
        else:
            # For overnight shifts, end should be before start
            if end_time >= start_time:
                report.add_warning(
                    f"{field_prefix}is_overnight",
                    f"Overnight flag is set but end time ({end_time}) is after "
                    f"start time ({start_time})",
                    is_overnight,
                )

    @staticmethod
    def validate_break_time(
        start_time: dt.time,
        end_time: dt.time,
        break_minutes: int,
        is_overnight: bool,
        report: ValidationReport,
    ) -> None:
        """Validate that break time is reasonable.

        Args:
            start_time: Work start time
            end_time: Work end time
            break_minutes: Break duration in minutes
            is_overnight: Whether shift spans midnight
            report: ValidationReport to collect issues
        """
        # Calculate work duration
        if is_overnight:
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            work_minutes = (24 * 60 - start_mins) + end_mins
        else:
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            work_minutes = end_mins - start_mins

        # Break must be less than work time
        if break_minutes >= work_minutes:
            report.add_error(
                "break_minutes",
                f"Break time ({break_minutes} min) must be less than "
                f"total work time ({work_minutes} min)",
                break_minutes,
            )
            return

        # Warn if break is more than 50% of work time
        if break_minutes > work_minutes * 0.5:
            report.add_warning(
                "break_minutes",
                f"Break time ({break_minutes} min) is unusually long "
                f"(> 50% of work time)",
                break_minutes,
            )

    @staticmethod
    def validate_profit_margin(
        cost_per_hour: Decimal,
        hourly_rate: Decimal,
        report: ValidationReport,
    ) -> None:
        """Validate that profit margin is positive.

        Args:
            cost_per_hour: Cost per hour
            hourly_rate: Billing rate per hour
            report: ValidationReport to collect issues
        """
        if cost_per_hour >= hourly_rate:
            report.add_error(
                "cost_per_hour",
                f"Cost per hour ({cost_per_hour}) must be less than "
                f"hourly rate ({hourly_rate}) to ensure profit",
                cost_per_hour,
            )
            return

        # Calculate profit margin percentage
        profit = hourly_rate - cost_per_hour
        profit_margin = (profit / hourly_rate) * 100

        # Warn if profit margin is very low (< 10%)
        if profit_margin < 10:
            report.add_warning(
                "cost_per_hour",
                f"Low profit margin ({profit_margin:.1f}%). "
                f"Cost is {cost_per_hour}, rate is {hourly_rate}",
                cost_per_hour,
            )

    @staticmethod
    def validate_work_duration(
        start_time: dt.time,
        end_time: dt.time,
        is_overnight: bool,
        report: ValidationReport,
    ) -> None:
        """Validate that work duration is reasonable.

        Args:
            start_time: Work start time
            end_time: Work end time
            is_overnight: Whether shift spans midnight
            report: ValidationReport to collect issues
        """
        # Calculate work duration in hours
        if is_overnight:
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            work_minutes = (24 * 60 - start_mins) + end_mins
        else:
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            work_minutes = end_mins - start_mins

        work_hours = work_minutes / 60

        # Warn if shift is unusually long (> 12 hours)
        if work_hours > 12:
            report.add_warning(
                "work_duration",
                f"Unusually long shift ({work_hours:.1f} hours)",
                work_minutes,
            )

        # Warn if shift is unusually short (< 2 hours)
        if work_hours < 2:
            report.add_warning(
                "work_duration",
                f"Unusually short shift ({work_hours:.1f} hours)",
                work_minutes,
            )

    @staticmethod
    def validate_timesheet_entry(
        entry: TimesheetEntry,
        report: ValidationReport,
    ) -> None:
        """Validate a complete timesheet entry for business rules.

        Args:
            entry: The timesheet entry to validate
            report: ValidationReport to collect issues
        """
        # Validate time range logic
        BusinessRuleValidators.validate_time_range(
            start_time=entry.start_time,
            end_time=entry.end_time,
            is_overnight=entry.is_overnight,
            field_prefix="",
            report=report,
        )

        # Validate break time
        BusinessRuleValidators.validate_break_time(
            start_time=entry.start_time,
            end_time=entry.end_time,
            break_minutes=entry.break_minutes,
            is_overnight=entry.is_overnight,
            report=report,
        )

        # Validate work duration
        BusinessRuleValidators.validate_work_duration(
            start_time=entry.start_time,
            end_time=entry.end_time,
            is_overnight=entry.is_overnight,
            report=report,
        )

    @staticmethod
    def validate_project_terms(
        terms: ProjectTerms,
        report: ValidationReport,
    ) -> None:
        """Validate project terms for business rules.

        Args:
            terms: The project terms to validate
            report: ValidationReport to collect issues
        """
        # Validate profit margin
        BusinessRuleValidators.validate_profit_margin(
            cost_per_hour=terms.cost_per_hour,
            hourly_rate=terms.hourly_rate,
            report=report,
        )

        # Note: Percentage validations (0-100) are handled by Pydantic model
        # so we don't need to duplicate them here
