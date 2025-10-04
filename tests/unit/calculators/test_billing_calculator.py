"""Unit tests for billing calculator.

This module tests the comprehensive billing calculation logic including:
- Complete billing breakdown for single entries
- Cost calculations
- Profit margin calculations
- Batch processing with rate lookups
- Aggregation of multiple billing results
"""

import datetime as dt
from decimal import Decimal

import pytest

from src.calculators.billing_calculator import (
    AggregateBillingResult,
    BillingResult,
    aggregate_billing,
    calculate_billing,
    calculate_billing_batch,
)
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


class TestCalculateBilling:
    """Test complete billing calculation for single entry."""

    def test_remote_work_no_travel(self):
        """Test billing for remote work with no travel."""
        entry = TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        )
        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        result = calculate_billing(entry, terms)

        # Verify hours breakdown
        assert result.billable_hours == Decimal("7.5")  # 8 - 0.5 break
        assert result.work_hours == Decimal("8.0")
        assert result.break_hours == Decimal("0.5")
        assert result.travel_hours == Decimal("0.0")

        # Verify revenue breakdown
        assert result.hours_billed == Decimal("637.50")  # 7.5 × 85
        assert result.travel_surcharge == Decimal("0.00")  # remote = no surcharge
        assert result.total_billed == Decimal("637.50")

        # Verify cost breakdown
        assert result.total_cost == Decimal("450.00")  # 7.5 × 60

        # Verify profit metrics
        assert result.profit == Decimal("187.50")  # 637.50 - 450.00
        assert result.profit_margin_percentage == Decimal(
            "29.41"
        )  # (187.50 / 637.50) × 100

    def test_onsite_work_with_travel_surcharge(self):
        """Test billing for on-site work with travel surcharge."""
        entry = TimesheetEntry(
            freelancer_name="Jane Smith",
            date=dt.date(2023, 6, 16),
            project_code="PROJ-002",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=60,
            location="onsite",
        )
        terms = ProjectTerms(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            hourly_rate=Decimal("100.00"),
            travel_surcharge_percentage=Decimal("20.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("70.00"),
        )

        result = calculate_billing(entry, terms)

        # Verify hours breakdown
        # 8 hours work - 0.5 break + (1 hour travel × 50%) = 8.0 billable
        assert result.billable_hours == Decimal("8.0")
        assert result.work_hours == Decimal("8.0")
        assert result.break_hours == Decimal("0.5")
        assert result.travel_hours == Decimal("0.5")  # 1 hour × 50%

        # Verify revenue breakdown
        assert result.hours_billed == Decimal("800.00")  # 8.0 × 100
        assert result.travel_surcharge == Decimal("160.00")  # 800 × 20%
        assert result.total_billed == Decimal("960.00")  # 800 + 160

        # Verify cost breakdown
        assert result.total_cost == Decimal("560.00")  # 8.0 × 70

        # Verify profit metrics
        assert result.profit == Decimal("400.00")  # 960 - 560
        assert result.profit_margin_percentage == Decimal("41.67")  # (400 / 960) × 100

    def test_overnight_shift_billing(self):
        """Test billing calculation for overnight shift."""
        entry = TimesheetEntry(
            freelancer_name="Night Worker",
            date=dt.date(2023, 6, 17),
            project_code="PROJ-003",
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )
        terms = ProjectTerms(
            freelancer_name="Night Worker",
            project_code="PROJ-003",
            hourly_rate=Decimal("90.00"),
            travel_surcharge_percentage=Decimal("10.0"),
            travel_time_percentage=Decimal("100.0"),
            cost_per_hour=Decimal("65.00"),
        )

        result = calculate_billing(entry, terms)

        # Verify hours breakdown (8 hour shift - 0.5 break)
        assert result.billable_hours == Decimal("7.5")
        assert result.work_hours == Decimal("8.0")
        assert result.break_hours == Decimal("0.5")

        # Verify revenue
        assert result.hours_billed == Decimal("675.00")  # 7.5 × 90
        assert result.total_billed == Decimal("675.00")

        # Verify cost and profit
        assert result.total_cost == Decimal("487.50")  # 7.5 × 65
        assert result.profit == Decimal("187.50")

    def test_full_day_with_travel(self):
        """Test billing for full workday with travel time."""
        entry = TimesheetEntry(
            freelancer_name="Traveler",
            date=dt.date(2023, 6, 18),
            project_code="PROJ-004",
            start_time=dt.time(8, 0),
            end_time=dt.time(18, 0),
            break_minutes=60,
            travel_time_minutes=120,
            location="onsite",
        )
        terms = ProjectTerms(
            freelancer_name="Traveler",
            project_code="PROJ-004",
            hourly_rate=Decimal("120.00"),
            travel_surcharge_percentage=Decimal("25.0"),
            travel_time_percentage=Decimal("100.0"),
            cost_per_hour=Decimal("80.00"),
        )

        result = calculate_billing(entry, terms)

        # 10 hours work - 1 hour break + 2 hours travel = 11 billable
        assert result.billable_hours == Decimal("11.0")
        assert result.work_hours == Decimal("10.0")
        assert result.break_hours == Decimal("1.0")
        assert result.travel_hours == Decimal("2.0")

        # Revenue: 11 × 120 = 1320, surcharge: 1320 × 25% = 330
        assert result.hours_billed == Decimal("1320.00")
        assert result.travel_surcharge == Decimal("330.00")
        assert result.total_billed == Decimal("1650.00")

        # Cost: 11 × 80 = 880
        assert result.total_cost == Decimal("880.00")
        assert result.profit == Decimal("770.00")

    def test_zero_profit_margin(self):
        """Test billing when cost equals revenue (zero profit)."""
        entry = TimesheetEntry(
            freelancer_name="Break Even",
            date=dt.date(2023, 6, 19),
            project_code="PROJ-005",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
        )
        # Note: ProjectTerms validation prevents cost >= rate,
        # so we use cost slightly less than rate
        terms = ProjectTerms(
            freelancer_name="Break Even",
            project_code="PROJ-005",
            hourly_rate=Decimal("100.00"),
            travel_surcharge_percentage=Decimal("0.0"),
            travel_time_percentage=Decimal("0.0"),
            cost_per_hour=Decimal("99.99"),
        )

        result = calculate_billing(entry, terms)

        assert result.billable_hours == Decimal("8.0")
        assert result.total_billed == Decimal("800.00")
        assert result.total_cost == Decimal("799.92")  # 8 × 99.99
        assert result.profit == Decimal("0.08")
        # Very small profit margin
        assert Decimal("0") < result.profit_margin_percentage < Decimal("1")

    def test_high_profit_margin(self):
        """Test billing with high profit margin."""
        entry = TimesheetEntry(
            freelancer_name="High Margin",
            date=dt.date(2023, 6, 20),
            project_code="PROJ-006",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=0,
            travel_time_minutes=0,
            location="remote",
        )
        terms = ProjectTerms(
            freelancer_name="High Margin",
            project_code="PROJ-006",
            hourly_rate=Decimal("200.00"),
            travel_surcharge_percentage=Decimal("0.0"),
            travel_time_percentage=Decimal("0.0"),
            cost_per_hour=Decimal("50.00"),
        )

        result = calculate_billing(entry, terms)

        assert result.total_billed == Decimal("1600.00")  # 8 × 200
        assert result.total_cost == Decimal("400.00")  # 8 × 50
        assert result.profit == Decimal("1200.00")
        assert result.profit_margin_percentage == Decimal("75.00")


class TestCalculateBillingBatch:
    """Test batch billing calculation with rate lookups."""

    def test_single_freelancer_multiple_projects(self):
        """Test batch calculation for one freelancer across multiple projects."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(13, 0),
                break_minutes=0,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-002",
                start_time=dt.time(14, 0),
                end_time=dt.time(18, 0),
                break_minutes=0,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        terms_map = {
            ("John Doe", "PROJ-001"): ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("85.00"),
                travel_surcharge_percentage=Decimal("0.0"),
                travel_time_percentage=Decimal("0.0"),
                cost_per_hour=Decimal("60.00"),
            ),
            ("John Doe", "PROJ-002"): ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-002",
                hourly_rate=Decimal("100.00"),
                travel_surcharge_percentage=Decimal("0.0"),
                travel_time_percentage=Decimal("0.0"),
                cost_per_hour=Decimal("70.00"),
            ),
        }

        results = calculate_billing_batch(entries, terms_map)

        assert len(results) == 2

        # First project: 4 hours × 85 = 340
        assert results[0].billable_hours == Decimal("4.0")
        assert results[0].total_billed == Decimal("340.00")
        assert results[0].total_cost == Decimal("240.00")  # 4 × 60
        assert results[0].profit == Decimal("100.00")

        # Second project: 4 hours × 100 = 400
        assert results[1].billable_hours == Decimal("4.0")
        assert results[1].total_billed == Decimal("400.00")
        assert results[1].total_cost == Decimal("280.00")  # 4 × 70
        assert results[1].profit == Decimal("120.00")

    def test_multiple_freelancers_same_project(self):
        """Test batch calculation for multiple freelancers on same project."""
        entries = [
            TimesheetEntry(
                freelancer_name="Alice",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Bob",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(10, 0),
                end_time=dt.time(18, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        terms_map = {
            ("Alice", "PROJ-001"): ProjectTerms(
                freelancer_name="Alice",
                project_code="PROJ-001",
                hourly_rate=Decimal("90.00"),
                travel_surcharge_percentage=Decimal("0.0"),
                travel_time_percentage=Decimal("0.0"),
                cost_per_hour=Decimal("65.00"),
            ),
            ("Bob", "PROJ-001"): ProjectTerms(
                freelancer_name="Bob",
                project_code="PROJ-001",
                hourly_rate=Decimal("95.00"),
                travel_surcharge_percentage=Decimal("0.0"),
                travel_time_percentage=Decimal("0.0"),
                cost_per_hour=Decimal("68.00"),
            ),
        }

        results = calculate_billing_batch(entries, terms_map)

        assert len(results) == 2

        # Alice: 7.5 hours × 90 = 675
        assert results[0].billable_hours == Decimal("7.5")
        assert results[0].total_billed == Decimal("675.00")

        # Bob: 7.5 hours × 95 = 712.50
        assert results[1].billable_hours == Decimal("7.5")
        assert results[1].total_billed == Decimal("712.50")

    def test_missing_terms_raises_error(self):
        """Test that missing terms for an entry raises KeyError."""
        entries = [
            TimesheetEntry(
                freelancer_name="Unknown",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-999",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=0,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        terms_map = {}  # Empty map - no terms available

        with pytest.raises(KeyError, match="Unknown.*PROJ-999"):
            calculate_billing_batch(entries, terms_map)

    def test_empty_batch(self):
        """Test batch calculation with empty list."""
        results = calculate_billing_batch([], {})
        assert results == []


class TestAggregateBilling:
    """Test aggregation of multiple billing results."""

    def test_aggregate_single_result(self):
        """Test aggregation of a single billing result."""
        results = [
            BillingResult(
                billable_hours=Decimal("8.0"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.0"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("800.00"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("800.00"),
                total_cost=Decimal("600.00"),
                profit=Decimal("200.00"),
                profit_margin_percentage=Decimal("25.00"),
            )
        ]

        aggregate = aggregate_billing(results)

        assert aggregate.total_hours == Decimal("8.0")
        assert aggregate.total_billed == Decimal("800.00")
        assert aggregate.total_cost == Decimal("600.00")
        assert aggregate.total_profit == Decimal("200.00")
        assert aggregate.average_profit_margin == Decimal("25.00")
        assert aggregate.entry_count == 1

    def test_aggregate_multiple_results(self):
        """Test aggregation of multiple billing results."""
        results = [
            BillingResult(
                billable_hours=Decimal("8.0"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.0"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("800.00"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("800.00"),
                total_cost=Decimal("600.00"),
                profit=Decimal("200.00"),
                profit_margin_percentage=Decimal("25.00"),
            ),
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("750.00"),
                travel_surcharge=Decimal("150.00"),
                total_billed=Decimal("900.00"),
                total_cost=Decimal("525.00"),
                profit=Decimal("375.00"),
                profit_margin_percentage=Decimal("41.67"),
            ),
            BillingResult(
                billable_hours=Decimal("6.0"),
                work_hours=Decimal("6.0"),
                break_hours=Decimal("0.0"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("600.00"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("600.00"),
                total_cost=Decimal("450.00"),
                profit=Decimal("150.00"),
                profit_margin_percentage=Decimal("25.00"),
            ),
        ]

        aggregate = aggregate_billing(results)

        assert aggregate.total_hours == Decimal("21.5")  # 8 + 7.5 + 6
        assert aggregate.total_billed == Decimal("2300.00")  # 800 + 900 + 600
        assert aggregate.total_cost == Decimal("1575.00")  # 600 + 525 + 450
        assert aggregate.total_profit == Decimal("725.00")  # 200 + 375 + 150
        # Average margin: (25 + 41.67 + 25) / 3 = 30.56 (rounded)
        assert aggregate.average_profit_margin == Decimal("30.56")
        assert aggregate.entry_count == 3

    def test_aggregate_zero_billed_handled_gracefully(self):
        """Test aggregation when total_billed is zero (edge case)."""
        results = [
            BillingResult(
                billable_hours=Decimal("0.0"),
                work_hours=Decimal("0.0"),
                break_hours=Decimal("0.0"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("0.00"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("0.00"),
                total_cost=Decimal("0.00"),
                profit=Decimal("0.00"),
                profit_margin_percentage=Decimal("0.00"),
            )
        ]

        aggregate = aggregate_billing(results)

        assert aggregate.total_hours == Decimal("0.0")
        assert aggregate.total_billed == Decimal("0.00")
        assert aggregate.total_cost == Decimal("0.00")
        assert aggregate.total_profit == Decimal("0.00")
        assert aggregate.average_profit_margin == Decimal("0.00")
        assert aggregate.entry_count == 1

    def test_aggregate_empty_list(self):
        """Test aggregation of empty list."""
        aggregate = aggregate_billing([])

        assert aggregate.total_hours == Decimal("0.0")
        assert aggregate.total_billed == Decimal("0.00")
        assert aggregate.total_cost == Decimal("0.00")
        assert aggregate.total_profit == Decimal("0.00")
        assert aggregate.average_profit_margin == Decimal("0.00")
        assert aggregate.entry_count == 0


class TestBillingResultDataclass:
    """Test BillingResult dataclass."""

    def test_billing_result_creation(self):
        """Test creating a BillingResult instance."""
        result = BillingResult(
            billable_hours=Decimal("8.0"),
            work_hours=Decimal("8.0"),
            break_hours=Decimal("0.0"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("800.00"),
            travel_surcharge=Decimal("0.00"),
            total_billed=Decimal("800.00"),
            total_cost=Decimal("600.00"),
            profit=Decimal("200.00"),
            profit_margin_percentage=Decimal("25.00"),
        )

        assert isinstance(result, BillingResult)
        assert result.billable_hours == Decimal("8.0")
        assert result.total_billed == Decimal("800.00")
        assert result.profit == Decimal("200.00")


class TestAggregateBillingResultDataclass:
    """Test AggregateBillingResult dataclass."""

    def test_aggregate_result_creation(self):
        """Test creating an AggregateBillingResult instance."""
        result = AggregateBillingResult(
            total_hours=Decimal("100.0"),
            total_billed=Decimal("10000.00"),
            total_cost=Decimal("7500.00"),
            total_profit=Decimal("2500.00"),
            average_profit_margin=Decimal("25.00"),
            entry_count=10,
        )

        assert isinstance(result, AggregateBillingResult)
        assert result.total_hours == Decimal("100.0")
        assert result.total_profit == Decimal("2500.00")
        assert result.entry_count == 10
