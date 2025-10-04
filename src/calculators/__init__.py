"""Calculator modules for billing system."""

from src.calculators.time_calculator import (
    BillableHoursResult,
    calculate_billable_amount,
    calculate_billable_hours,
    calculate_travel_surcharge,
    calculate_work_duration,
)
from src.calculators.time_utils import (
    calculate_duration_minutes,
    convert_time_to_minutes,
    minutes_to_timedelta,
    timedelta_to_decimal_hours,
)

__all__ = [
    # time_calculator
    "BillableHoursResult",
    "calculate_billable_amount",
    "calculate_billable_hours",
    "calculate_travel_surcharge",
    "calculate_work_duration",
    # time_utils
    "calculate_duration_minutes",
    "convert_time_to_minutes",
    "minutes_to_timedelta",
    "timedelta_to_decimal_hours",
]
