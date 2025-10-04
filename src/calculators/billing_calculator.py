"""Billing calculator for comprehensive financial calculations.

This module implements complete billing calculations including:
- Complete billing breakdown for single entries
- Cost calculations
- Profit margin calculations
- Batch processing with rate lookups
- Aggregation of multiple billing results

The calculations build upon the time_calculator module and provide
comprehensive financial metrics for billing and reporting.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from src.calculators.time_calculator import (
    calculate_billable_hours,
    calculate_travel_surcharge,
)
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


@dataclass
class BillingResult:
    """Complete billing breakdown for a single timesheet entry.

    This dataclass contains all financial metrics for a timesheet entry,
    including hours breakdown, revenue breakdown, costs, and profit margins.

    Attributes:
        billable_hours: Total billable hours (work - break + travel%)
        work_hours: Raw work hours (end - start)
        break_hours: Break hours deducted
        travel_hours: Billable travel hours (travel_time × percentage)
        hours_billed: Revenue from hours (billable_hours × hourly_rate)
        travel_surcharge: Additional charge for on-site work
        total_billed: Total revenue (hours_billed + travel_surcharge)
        total_cost: Total cost (billable_hours × cost_per_hour)
        profit: Profit (total_billed - total_cost)
        profit_margin_percentage: Profit margin ((profit / total_billed) × 100)

    Example:
        >>> result = BillingResult(
        ...     billable_hours=Decimal("8.0"),
        ...     work_hours=Decimal("8.0"),
        ...     break_hours=Decimal("0.0"),
        ...     travel_hours=Decimal("0.0"),
        ...     hours_billed=Decimal("800.00"),
        ...     travel_surcharge=Decimal("0.00"),
        ...     total_billed=Decimal("800.00"),
        ...     total_cost=Decimal("600.00"),
        ...     profit=Decimal("200.00"),
        ...     profit_margin_percentage=Decimal("25.00"),
        ... )
        >>> result.profit
        Decimal('200.00')
    """

    billable_hours: Decimal
    work_hours: Decimal
    break_hours: Decimal
    travel_hours: Decimal
    hours_billed: Decimal
    travel_surcharge: Decimal
    total_billed: Decimal
    total_cost: Decimal
    profit: Decimal
    profit_margin_percentage: Decimal


@dataclass
class AggregateBillingResult:
    """Aggregated billing summary for multiple entries.

    This dataclass contains aggregated financial metrics across multiple
    timesheet entries, useful for reporting and analysis.

    Attributes:
        total_hours: Sum of all billable hours
        total_billed: Sum of all billing amounts
        total_cost: Sum of all costs
        total_profit: Sum of all profits
        average_profit_margin: Average profit margin percentage
        entry_count: Number of entries aggregated

    Example:
        >>> result = AggregateBillingResult(
        ...     total_hours=Decimal("100.0"),
        ...     total_billed=Decimal("10000.00"),
        ...     total_cost=Decimal("7500.00"),
        ...     total_profit=Decimal("2500.00"),
        ...     average_profit_margin=Decimal("25.00"),
        ...     entry_count=10,
        ... )
        >>> result.total_profit
        Decimal('2500.00')
    """

    total_hours: Decimal
    total_billed: Decimal
    total_cost: Decimal
    total_profit: Decimal
    average_profit_margin: Decimal
    entry_count: int


def calculate_billing(entry: TimesheetEntry, terms: ProjectTerms) -> BillingResult:
    """Calculate complete billing breakdown for a single timesheet entry.

    This function provides a comprehensive financial breakdown including:
    - Hours breakdown (work, break, travel, billable)
    - Revenue breakdown (hours billed, travel surcharge, total)
    - Cost breakdown
    - Profit metrics (profit, margin percentage)

    Args:
        entry: Timesheet entry with work details
        terms: Project terms with rates and costs

    Returns:
        BillingResult with complete financial breakdown

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=30,
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
        >>> result = calculate_billing(entry, terms)
        >>> result.total_billed
        Decimal('637.50')
    """
    # Calculate billable hours breakdown
    billable_hours_result = calculate_billable_hours(entry, terms)

    # Calculate revenue breakdown
    hours_billed = (billable_hours_result.total_hours * terms.hourly_rate).quantize(
        Decimal("0.01")
    )
    travel_surcharge = calculate_travel_surcharge(entry, terms)
    total_billed = (hours_billed + travel_surcharge).quantize(Decimal("0.01"))

    # Calculate cost breakdown
    total_cost = (billable_hours_result.total_hours * terms.cost_per_hour).quantize(
        Decimal("0.01")
    )

    # Calculate profit metrics
    profit = (total_billed - total_cost).quantize(Decimal("0.01"))

    # Calculate profit margin percentage
    if total_billed > Decimal("0"):
        profit_margin_percentage = ((profit / total_billed) * Decimal("100")).quantize(
            Decimal("0.01")
        )
    else:
        profit_margin_percentage = Decimal("0.00")

    return BillingResult(
        billable_hours=billable_hours_result.total_hours,
        work_hours=billable_hours_result.work_hours,
        break_hours=billable_hours_result.break_hours,
        travel_hours=billable_hours_result.travel_hours,
        hours_billed=hours_billed,
        travel_surcharge=travel_surcharge,
        total_billed=total_billed,
        total_cost=total_cost,
        profit=profit,
        profit_margin_percentage=profit_margin_percentage,
    )


def calculate_billing_batch(
    entries: List[TimesheetEntry],
    terms_map: Dict[Tuple[str, str], ProjectTerms],
) -> List[BillingResult]:
    """Calculate billing for multiple entries with rate lookups.

    This function processes multiple timesheet entries and looks up the
    appropriate billing terms for each freelancer-project combination.

    Args:
        entries: List of timesheet entries to process
        terms_map: Dictionary mapping (freelancer_name, project_code) to ProjectTerms

    Returns:
        List of BillingResult objects in the same order as entries

    Raises:
        KeyError: If terms are not found for a freelancer-project combination

    Example:
        >>> entries = [
        ...     TimesheetEntry(
        ...         freelancer_name="John Doe",
        ...         date=dt.date(2023, 6, 15),
        ...         project_code="PROJ-001",
        ...         start_time=dt.time(9, 0),
        ...         end_time=dt.time(17, 0),
        ...         break_minutes=0,
        ...         travel_time_minutes=0,
        ...         location="remote",
        ...     )
        ... ]
        >>> terms_map = {
        ...     ("John Doe", "PROJ-001"): ProjectTerms(
        ...         freelancer_name="John Doe",
        ...         project_code="PROJ-001",
        ...         hourly_rate=Decimal("85.00"),
        ...         travel_surcharge_percentage=Decimal("0.0"),
        ...         travel_time_percentage=Decimal("0.0"),
        ...         cost_per_hour=Decimal("60.00"),
        ...     )
        ... }
        >>> results = calculate_billing_batch(entries, terms_map)
        >>> len(results)
        1
    """
    results = []

    for entry in entries:
        # Look up terms for this freelancer-project combination
        key = (entry.freelancer_name, entry.project_code)
        try:
            terms = terms_map[key]
        except KeyError:
            raise KeyError(
                f"No billing terms found for freelancer '{entry.freelancer_name}' "
                f"on project '{entry.project_code}'"
            )

        # Calculate billing for this entry
        result = calculate_billing(entry, terms)
        results.append(result)

    return results


def aggregate_billing(results: List[BillingResult]) -> AggregateBillingResult:
    """Aggregate multiple billing results into a summary.

    This function combines multiple billing results to provide aggregate
    financial metrics across all entries.

    Args:
        results: List of BillingResult objects to aggregate

    Returns:
        AggregateBillingResult with aggregated metrics

    Example:
        >>> results = [
        ...     BillingResult(
        ...         billable_hours=Decimal("8.0"),
        ...         work_hours=Decimal("8.0"),
        ...         break_hours=Decimal("0.0"),
        ...         travel_hours=Decimal("0.0"),
        ...         hours_billed=Decimal("800.00"),
        ...         travel_surcharge=Decimal("0.00"),
        ...         total_billed=Decimal("800.00"),
        ...         total_cost=Decimal("600.00"),
        ...         profit=Decimal("200.00"),
        ...         profit_margin_percentage=Decimal("25.00"),
        ...     )
        ... ]
        >>> aggregate = aggregate_billing(results)
        >>> aggregate.total_profit
        Decimal('200.00')
    """
    # Handle empty list
    if not results:
        return AggregateBillingResult(
            total_hours=Decimal("0.0"),
            total_billed=Decimal("0.00"),
            total_cost=Decimal("0.00"),
            total_profit=Decimal("0.00"),
            average_profit_margin=Decimal("0.00"),
            entry_count=0,
        )

    # Sum up all metrics
    total_hours = sum(r.billable_hours for r in results)
    total_billed = sum(r.total_billed for r in results)
    total_cost = sum(r.total_cost for r in results)
    total_profit = sum(r.profit for r in results)

    # Calculate average profit margin
    sum_margins = sum(r.profit_margin_percentage for r in results)
    average_profit_margin = (sum_margins / len(results)).quantize(Decimal("0.01"))

    return AggregateBillingResult(
        total_hours=total_hours,
        total_billed=total_billed.quantize(Decimal("0.01")),
        total_cost=total_cost.quantize(Decimal("0.01")),
        total_profit=total_profit.quantize(Decimal("0.01")),
        average_profit_margin=average_profit_margin,
        entry_count=len(results),
    )
