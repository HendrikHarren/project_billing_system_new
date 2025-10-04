"""Time calculation engine for billing system.

This module implements the business logic for calculating:
- Work duration (End - Start)
- Billable hours (Work - Break + Travel%)
- Billable amounts (Hours × Rate)
- Travel surcharges for on-site work

The calculations match the formula from the Jupyter notebook:
Hours = End - Start - Break + (Travel% × TravelTime)
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from src.calculators.time_utils import (
    calculate_duration_minutes,
    minutes_to_timedelta,
    timedelta_to_decimal_hours,
)
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


@dataclass
class BillableHoursResult:
    """Result of billable hours calculation.

    Attributes:
        total_hours: Total billable hours (work - break + travel%)
        work_hours: Raw work hours (end - start)
        break_hours: Break hours deducted
        travel_hours: Billable travel hours (travel_time × percentage)
    """

    total_hours: Decimal
    work_hours: Decimal
    break_hours: Decimal
    travel_hours: Decimal


def calculate_work_duration(entry: TimesheetEntry) -> dt.timedelta:
    """Calculate the total work duration (end - start).

    This calculates the raw work duration without accounting for breaks.
    Handles overnight shifts correctly.

    Args:
        entry: Timesheet entry

    Returns:
        Work duration as timedelta

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=0,
        ...     travel_time_minutes=0,
        ...     location="remote",
        ... )
        >>> calculate_work_duration(entry)
        datetime.timedelta(seconds=28800)
    """
    duration_minutes = calculate_duration_minutes(
        entry.start_time, entry.end_time, entry.is_overnight
    )
    return minutes_to_timedelta(duration_minutes)


def calculate_billable_hours(
    entry: TimesheetEntry, terms: ProjectTerms
) -> BillableHoursResult:
    """Calculate billable hours with breaks and travel time.

    Formula: Billable = (End - Start) - Break + (Travel% × TravelTime)

    Args:
        entry: Timesheet entry with work details
        terms: Project terms with travel percentage

    Returns:
        BillableHoursResult with detailed breakdown

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=30,
        ...     travel_time_minutes=60,
        ...     location="onsite",
        ... )
        >>> terms = ProjectTerms(
        ...     freelancer_name="John Doe",
        ...     project_code="PROJ-001",
        ...     hourly_rate=Decimal("85.00"),
        ...     travel_surcharge_percentage=Decimal("15.0"),
        ...     travel_time_percentage=Decimal("50.0"),
        ...     cost_per_hour=Decimal("60.00"),
        ... )
        >>> result = calculate_billable_hours(entry, terms)
        >>> result.total_hours
        Decimal('8.00')
    """
    # Calculate work duration (end - start)
    work_duration = calculate_work_duration(entry)
    work_hours = timedelta_to_decimal_hours(work_duration)

    # Calculate break hours
    break_duration = dt.timedelta(minutes=entry.break_minutes)
    break_hours = timedelta_to_decimal_hours(break_duration)

    # Calculate billable travel hours (travel_time × percentage)
    travel_duration = dt.timedelta(minutes=entry.travel_time_minutes)
    travel_hours_total = timedelta_to_decimal_hours(travel_duration)
    travel_percentage = terms.travel_time_percentage / Decimal("100")
    travel_hours = travel_hours_total * travel_percentage

    # Calculate total billable hours
    total_hours = work_hours - break_hours + travel_hours

    return BillableHoursResult(
        total_hours=total_hours,
        work_hours=work_hours,
        break_hours=break_hours,
        travel_hours=travel_hours,
    )


def calculate_billable_amount(entry: TimesheetEntry, terms: ProjectTerms) -> Decimal:
    """Calculate the billable amount (hours × rate).

    Args:
        entry: Timesheet entry
        terms: Project terms with hourly rate

    Returns:
        Billable amount in currency units (2 decimal precision)

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=0,
        ...     travel_time_minutes=0,
        ...     location="remote",
        ... )
        >>> terms = ProjectTerms(
        ...     freelancer_name="John Doe",
        ...     project_code="PROJ-001",
        ...     hourly_rate=Decimal("85.00"),
        ...     travel_surcharge_percentage=Decimal("15.0"),
        ...     travel_time_percentage=Decimal("50.0"),
        ...     cost_per_hour=Decimal("60.00"),
        ... )
        >>> calculate_billable_amount(entry, terms)
        Decimal('680.00')
    """
    billable_hours_result = calculate_billable_hours(entry, terms)
    amount = billable_hours_result.total_hours * terms.hourly_rate
    return amount.quantize(Decimal("0.01"))


def calculate_travel_surcharge(entry: TimesheetEntry, terms: ProjectTerms) -> Decimal:
    """Calculate travel surcharge for on-site work.

    The surcharge only applies when location is 'onsite'.
    Formula: (Billable Hours × Rate) × Surcharge%

    Args:
        entry: Timesheet entry
        terms: Project terms with surcharge percentage

    Returns:
        Travel surcharge amount (0.00 for remote work)

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=30,
        ...     travel_time_minutes=0,
        ...     location="onsite",
        ... )
        >>> terms = ProjectTerms(
        ...     freelancer_name="John Doe",
        ...     project_code="PROJ-001",
        ...     hourly_rate=Decimal("85.00"),
        ...     travel_surcharge_percentage=Decimal("15.0"),
        ...     travel_time_percentage=Decimal("50.0"),
        ...     cost_per_hour=Decimal("60.00"),
        ... )
        >>> calculate_travel_surcharge(entry, terms)
        Decimal('95.63')
    """
    # No surcharge for remote work
    if entry.location == "remote":
        return Decimal("0.00")

    # Calculate base billable amount
    billable_hours_result = calculate_billable_hours(entry, terms)
    base_amount = billable_hours_result.total_hours * terms.hourly_rate

    # Apply surcharge percentage
    surcharge_percentage = terms.travel_surcharge_percentage / Decimal("100")
    surcharge = base_amount * surcharge_percentage

    return surcharge.quantize(Decimal("0.01"))
