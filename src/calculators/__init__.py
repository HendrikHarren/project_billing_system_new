"""Calculator modules for billing system."""

from src.calculators.billing_calculator import (
    AggregateBillingResult,
    BillingResult,
    aggregate_billing,
    calculate_billing,
    calculate_billing_batch,
)
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
from src.calculators.trip_calculator import calculate_trips

__all__ = [
    # billing_calculator
    "AggregateBillingResult",
    "BillingResult",
    "aggregate_billing",
    "calculate_billing",
    "calculate_billing_batch",
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
    # trip_calculator
    "calculate_trips",
]
