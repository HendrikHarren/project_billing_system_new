"""Time calculation utilities for the billing system.

This module provides low-level utilities for time calculations including:
- Converting time to minutes
- Calculating durations between times (with overnight support)
- Converting between timedelta and decimal hours

These utilities are timezone-agnostic and work with dt.time and dt.timedelta.
"""

import datetime as dt
from decimal import Decimal


def convert_time_to_minutes(time: dt.time) -> int:
    """Convert a dt.time object to minutes since midnight.

    Args:
        time: The time to convert

    Returns:
        Number of minutes since midnight (0-1439)

    Example:
        >>> convert_time_to_minutes(dt.time(9, 30))
        570
        >>> convert_time_to_minutes(dt.time(0, 0))
        0
        >>> convert_time_to_minutes(dt.time(23, 59))
        1439
    """
    return time.hour * 60 + time.minute


def calculate_duration_minutes(
    start_time: dt.time, end_time: dt.time, is_overnight: bool = False
) -> int:
    """Calculate duration in minutes between two times.

    Args:
        start_time: Start time
        end_time: End time
        is_overnight: True if shift spans midnight (end is next day)

    Returns:
        Duration in minutes

    Example:
        >>> calculate_duration_minutes(dt.time(9, 0), dt.time(17, 0), False)
        480
        >>> calculate_duration_minutes(dt.time(22, 0), dt.time(6, 0), True)
        480
        >>> calculate_duration_minutes(dt.time(22, 0), dt.time(0, 0), True)
        120

    Note:
        When is_overnight=True and end_time=00:00, this represents the next day.
        Same times with is_overnight=True represents a full 24-hour period.
    """
    start_minutes = convert_time_to_minutes(start_time)
    end_minutes = convert_time_to_minutes(end_time)

    if is_overnight:
        # Calculate across midnight
        # e.g., 22:00 (1320) to 06:00 (360) = (1440 - 1320) + 360 = 480
        return (24 * 60 - start_minutes) + end_minutes
    else:
        # Normal calculation
        return end_minutes - start_minutes


def minutes_to_timedelta(minutes: int) -> dt.timedelta:
    """Convert minutes to a timedelta object.

    Args:
        minutes: Number of minutes

    Returns:
        Timedelta representing the duration

    Example:
        >>> minutes_to_timedelta(60)
        datetime.timedelta(seconds=3600)
        >>> minutes_to_timedelta(480)
        datetime.timedelta(seconds=28800)
    """
    return dt.timedelta(minutes=minutes)


def timedelta_to_decimal_hours(td: dt.timedelta) -> Decimal:
    """Convert a timedelta to decimal hours with 2 decimal precision.

    Args:
        td: Timedelta to convert

    Returns:
        Decimal hours (rounded to 2 decimal places)

    Example:
        >>> timedelta_to_decimal_hours(dt.timedelta(hours=8))
        Decimal('8.00')
        >>> timedelta_to_decimal_hours(dt.timedelta(hours=7, minutes=30))
        Decimal('7.50')
        >>> timedelta_to_decimal_hours(dt.timedelta(minutes=15))
        Decimal('0.25')

    Note:
        Rounds to 2 decimal places using ROUND_HALF_UP.
        For example, 10 minutes (0.166666...) rounds to 0.17.
    """
    total_seconds = td.total_seconds()
    hours = Decimal(str(total_seconds)) / Decimal("3600")
    # Round to 2 decimal places
    return hours.quantize(Decimal("0.01"))
