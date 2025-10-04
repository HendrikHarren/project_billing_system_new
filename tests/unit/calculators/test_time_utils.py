"""Unit tests for time utility functions.

This module tests the low-level time calculation utilities used
throughout the billing system.
"""

import datetime as dt
from decimal import Decimal

from src.calculators.time_utils import (
    calculate_duration_minutes,
    convert_time_to_minutes,
    minutes_to_timedelta,
    timedelta_to_decimal_hours,
)


class TestConvertTimeToMinutes:
    """Test converting dt.time to minutes since midnight."""

    def test_midnight(self):
        """Test that midnight (00:00) converts to 0 minutes."""
        assert convert_time_to_minutes(dt.time(0, 0)) == 0

    def test_noon(self):
        """Test that noon (12:00) converts to 720 minutes."""
        assert convert_time_to_minutes(dt.time(12, 0)) == 720

    def test_end_of_day(self):
        """Test that 23:59 converts to 1439 minutes."""
        assert convert_time_to_minutes(dt.time(23, 59)) == 1439

    def test_morning_time(self):
        """Test a typical morning time (9:30)."""
        assert convert_time_to_minutes(dt.time(9, 30)) == 570

    def test_afternoon_time(self):
        """Test a typical afternoon time (17:45)."""
        assert convert_time_to_minutes(dt.time(17, 45)) == 1065


class TestCalculateDurationMinutes:
    """Test duration calculation between two times."""

    def test_normal_shift(self):
        """Test a normal day shift (9:00 to 17:00)."""
        start = dt.time(9, 0)
        end = dt.time(17, 0)
        assert calculate_duration_minutes(start, end, is_overnight=False) == 480

    def test_same_time_not_overnight(self):
        """Test same start and end time (not overnight) returns 0."""
        start = dt.time(9, 0)
        end = dt.time(9, 0)
        assert calculate_duration_minutes(start, end, is_overnight=False) == 0

    def test_overnight_shift(self):
        """Test an overnight shift (22:00 to 06:00)."""
        start = dt.time(22, 0)
        end = dt.time(6, 0)
        assert calculate_duration_minutes(start, end, is_overnight=True) == 480

    def test_overnight_ending_at_midnight(self):
        """Test overnight shift ending at midnight (22:00 to 00:00)."""
        start = dt.time(22, 0)
        end = dt.time(0, 0)
        assert calculate_duration_minutes(start, end, is_overnight=True) == 120

    def test_overnight_starting_at_midnight(self):
        """Test overnight shift starting at midnight (00:00 to 08:00)."""
        start = dt.time(0, 0)
        end = dt.time(8, 0)
        assert calculate_duration_minutes(start, end, is_overnight=True) == 1440 + 480

    def test_same_time_overnight(self):
        """Test same time overnight (full 24 hours)."""
        start = dt.time(0, 0)
        end = dt.time(0, 0)
        assert calculate_duration_minutes(start, end, is_overnight=True) == 1440


class TestMinutesToTimedelta:
    """Test converting minutes to timedelta."""

    def test_zero_minutes(self):
        """Test that 0 minutes converts to zero timedelta."""
        assert minutes_to_timedelta(0) == dt.timedelta(0)

    def test_one_hour(self):
        """Test that 60 minutes converts to 1 hour."""
        assert minutes_to_timedelta(60) == dt.timedelta(hours=1)

    def test_eight_hours(self):
        """Test that 480 minutes converts to 8 hours."""
        assert minutes_to_timedelta(480) == dt.timedelta(hours=8)

    def test_with_partial_hour(self):
        """Test that 90 minutes converts to 1.5 hours."""
        assert minutes_to_timedelta(90) == dt.timedelta(hours=1, minutes=30)

    def test_full_day(self):
        """Test that 1440 minutes converts to 24 hours."""
        assert minutes_to_timedelta(1440) == dt.timedelta(hours=24)


class TestTimedeltaToDecimalHours:
    """Test converting timedelta to decimal hours."""

    def test_zero_timedelta(self):
        """Test that zero timedelta converts to 0.0 hours."""
        assert timedelta_to_decimal_hours(dt.timedelta(0)) == Decimal("0.00")

    def test_one_hour(self):
        """Test that 1 hour converts to 1.00."""
        assert timedelta_to_decimal_hours(dt.timedelta(hours=1)) == Decimal("1.00")

    def test_eight_hours(self):
        """Test that 8 hours converts to 8.00."""
        assert timedelta_to_decimal_hours(dt.timedelta(hours=8)) == Decimal("8.00")

    def test_half_hour(self):
        """Test that 30 minutes converts to 0.50 hours."""
        assert timedelta_to_decimal_hours(dt.timedelta(minutes=30)) == Decimal("0.50")

    def test_quarter_hour(self):
        """Test that 15 minutes converts to 0.25 hours."""
        assert timedelta_to_decimal_hours(dt.timedelta(minutes=15)) == Decimal("0.25")

    def test_complex_duration(self):
        """Test that 7 hours 45 minutes converts to 7.75."""
        td = dt.timedelta(hours=7, minutes=45)
        assert timedelta_to_decimal_hours(td) == Decimal("7.75")

    def test_ten_minute_precision(self):
        """Test that 10 minutes converts to 0.17 (rounded)."""
        td = dt.timedelta(minutes=10)
        result = timedelta_to_decimal_hours(td)
        # 10/60 = 0.166666... should round to 0.17
        assert result == Decimal("0.17")
