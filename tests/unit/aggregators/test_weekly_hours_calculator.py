"""Tests for weekly hours calculator module.

This module contains comprehensive tests for the WeeklyHoursCalculator class,
which generates weekly capacity and utilization reports from timesheet data.
"""

import datetime as dt
from decimal import Decimal
from typing import List

import pandas as pd
import pytest

from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
from src.aggregators.weekly_hours_calculator import (
    WeeklyHoursCalculator,
    WeeklyHoursData,
)
from src.calculators.billing_calculator import BillingResult
from src.models.timesheet import TimesheetEntry


@pytest.fixture
def sample_entries_single_week() -> List[TimesheetEntry]:
    """Create sample entries for a single week."""
    return [
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 12),  # Monday, Week 24
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 13),  # Tuesday, Week 24
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(18, 0),
            break_minutes=60,
            travel_time_minutes=0,
            location="remote",
        ),
    ]


@pytest.fixture
def sample_entries_multiple_weeks() -> List[TimesheetEntry]:
    """Create sample entries across multiple weeks."""
    return [
        # Week 24
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 12),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
        # Week 25
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 19),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
        # Week 26
        TimesheetEntry(
            freelancer_name="Jane Smith",
            date=dt.date(2023, 6, 26),
            project_code="PROJ-002",
            start_time=dt.time(10, 0),
            end_time=dt.time(18, 0),
            break_minutes=60,
            travel_time_minutes=0,
            location="remote",
        ),
    ]


@pytest.fixture
def sample_entries_year_boundary() -> List[TimesheetEntry]:
    """Create sample entries across year boundary."""
    return [
        # 2023 Week 52 (Dec 25-31)
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 12, 28),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
        # 2024 Week 1 (Jan 1-7)
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2024, 1, 2),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
    ]


@pytest.fixture
def sample_billing_results() -> List[BillingResult]:
    """Create sample billing results matching entries."""
    return [
        BillingResult(
            billable_hours=Decimal("7.5"),
            work_hours=Decimal("8.0"),
            break_hours=Decimal("0.5"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("637.50"),
            travel_surcharge=Decimal("0.00"),
            total_billed=Decimal("637.50"),
            total_cost=Decimal("450.00"),
            profit=Decimal("187.50"),
            profit_margin_percentage=Decimal("29.41"),
        ),
        BillingResult(
            billable_hours=Decimal("8.0"),
            work_hours=Decimal("9.0"),
            break_hours=Decimal("1.0"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("680.00"),
            travel_surcharge=Decimal("0.00"),
            total_billed=Decimal("680.00"),
            total_cost=Decimal("480.00"),
            profit=Decimal("200.00"),
            profit_margin_percentage=Decimal("29.41"),
        ),
    ]


@pytest.fixture
def calculator():
    """Create WeeklyHoursCalculator instance for testing."""
    return WeeklyHoursCalculator()


class TestWeeklyHoursCalculatorInit:
    """Test WeeklyHoursCalculator initialization."""

    def test_init_creates_instance(self):
        """Test that constructor creates instance successfully."""
        calculator = WeeklyHoursCalculator()
        assert calculator is not None


class TestCalculateWeeklyHours:
    """Test calculating weekly hours from aggregated data."""

    def test_single_freelancer_single_week(
        self, calculator, sample_entries_single_week, sample_billing_results
    ):
        """Test calculating weekly hours for single freelancer in one week."""
        data = AggregatedTimesheetData(
            entries=sample_entries_single_week,
            billing_results=sample_billing_results,
            trips=[],
        )

        result = calculator.calculate_weekly_hours(data)

        assert len(result) == 1
        assert result[0].freelancer_name == "John Doe"
        assert result[0].year == 2023
        assert result[0].week_number == 24
        assert result[0].billable_hours == Decimal("15.5")  # 7.5 + 8.0
        assert result[0].work_hours == Decimal("17.0")  # 8.0 + 9.0
        assert result[0].entries_count == 2

    def test_multiple_freelancers_multiple_weeks(
        self, calculator, sample_entries_multiple_weeks
    ):
        """Test calculating weekly hours across multiple weeks and freelancers."""
        # Create billing results for all entries
        billing_results = [
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("637.50"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("637.50"),
                total_cost=Decimal("450.00"),
                profit=Decimal("187.50"),
                profit_margin_percentage=Decimal("29.41"),
            )
            for _ in range(3)
        ]

        data = AggregatedTimesheetData(
            entries=sample_entries_multiple_weeks,
            billing_results=billing_results,
            trips=[],
        )

        result = calculator.calculate_weekly_hours(data)

        # Should have 3 weekly records (John week 24, John week 25, Jane week 26)
        assert len(result) == 3

        # Verify each record
        john_week_24 = [
            r for r in result if r.freelancer_name == "John Doe" and r.week_number == 24
        ][0]
        assert john_week_24.billable_hours == Decimal("7.5")
        assert john_week_24.entries_count == 1

        john_week_25 = [
            r for r in result if r.freelancer_name == "John Doe" and r.week_number == 25
        ][0]
        assert john_week_25.billable_hours == Decimal("7.5")

        jane_week_26 = [
            r
            for r in result
            if r.freelancer_name == "Jane Smith" and r.week_number == 26
        ][0]
        assert jane_week_26.billable_hours == Decimal("7.5")

    def test_year_boundary_handling(self, calculator, sample_entries_year_boundary):
        """Test correct handling of year boundaries."""
        billing_results = [
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("637.50"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("637.50"),
                total_cost=Decimal("450.00"),
                profit=Decimal("187.50"),
                profit_margin_percentage=Decimal("29.41"),
            )
            for _ in range(2)
        ]

        data = AggregatedTimesheetData(
            entries=sample_entries_year_boundary,
            billing_results=billing_results,
            trips=[],
        )

        result = calculator.calculate_weekly_hours(data)

        # Should have 2 weekly records (2023 week 52, 2024 week 1)
        assert len(result) == 2

        week_52_2023 = [r for r in result if r.year == 2023 and r.week_number == 52][0]
        assert week_52_2023.billable_hours == Decimal("7.5")

        week_1_2024 = [r for r in result if r.year == 2024 and r.week_number == 1][0]
        assert week_1_2024.billable_hours == Decimal("7.5")

    def test_empty_dataset(self, calculator):
        """Test handling of empty dataset."""
        data = AggregatedTimesheetData(entries=[], billing_results=[], trips=[])

        result = calculator.calculate_weekly_hours(data)

        assert result == []

    def test_overnight_shift_handling(self, calculator):
        """Test correct calculation for overnight shifts."""
        overnight_entry = TimesheetEntry(
            freelancer_name="Night Worker",
            date=dt.date(2023, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(22, 0),
            end_time=dt.time(6, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
            is_overnight=True,
        )

        billing_result = BillingResult(
            billable_hours=Decimal("7.5"),
            work_hours=Decimal("8.0"),
            break_hours=Decimal("0.5"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("637.50"),
            travel_surcharge=Decimal("0.00"),
            total_billed=Decimal("637.50"),
            total_cost=Decimal("450.00"),
            profit=Decimal("187.50"),
            profit_margin_percentage=Decimal("29.41"),
        )

        data = AggregatedTimesheetData(
            entries=[overnight_entry], billing_results=[billing_result], trips=[]
        )

        result = calculator.calculate_weekly_hours(data)

        assert len(result) == 1
        assert result[0].billable_hours == Decimal("7.5")


class TestGenerateWeeklyMatrix:
    """Test generating weekly matrix format."""

    def test_generate_matrix_basic(self, calculator):
        """Test basic matrix generation."""
        weekly_data = [
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=24,
                billable_hours=Decimal("40.0"),
                work_hours=Decimal("45.0"),
                entries_count=5,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=25,
                billable_hours=Decimal("32.0"),
                work_hours=Decimal("36.0"),
                entries_count=4,
            ),
            WeeklyHoursData(
                freelancer_name="Jane Smith",
                year=2023,
                week_number=24,
                billable_hours=Decimal("35.0"),
                work_hours=Decimal("40.0"),
                entries_count=5,
            ),
        ]

        matrix = calculator.generate_weekly_matrix(weekly_data)

        assert isinstance(matrix, pd.DataFrame)
        assert len(matrix) == 2  # 2 freelancers
        assert "John Doe" in matrix.index
        assert "Jane Smith" in matrix.index
        assert "2023-W24" in matrix.columns
        assert "2023-W25" in matrix.columns
        assert matrix.loc["John Doe", "2023-W24"] == Decimal("40.0")
        assert matrix.loc["John Doe", "2023-W25"] == Decimal("32.0")
        assert matrix.loc["Jane Smith", "2023-W24"] == Decimal("35.0")
        # Jane has no entry for week 25, should be 0 or NaN
        assert pd.isna(matrix.loc["Jane Smith", "2023-W25"]) or matrix.loc[
            "Jane Smith", "2023-W25"
        ] == Decimal("0.0")

    def test_generate_matrix_year_boundary(self, calculator):
        """Test matrix generation across year boundary."""
        weekly_data = [
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=52,
                billable_hours=Decimal("40.0"),
                work_hours=Decimal("45.0"),
                entries_count=5,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2024,
                week_number=1,
                billable_hours=Decimal("32.0"),
                work_hours=Decimal("36.0"),
                entries_count=4,
            ),
        ]

        matrix = calculator.generate_weekly_matrix(weekly_data)

        assert isinstance(matrix, pd.DataFrame)
        assert "2023-W52" in matrix.columns
        assert "2024-W01" in matrix.columns
        assert matrix.loc["John Doe", "2023-W52"] == Decimal("40.0")
        assert matrix.loc["John Doe", "2024-W01"] == Decimal("32.0")

    def test_generate_matrix_empty_data(self, calculator):
        """Test matrix generation with empty data."""
        matrix = calculator.generate_weekly_matrix([])

        assert isinstance(matrix, pd.DataFrame)
        assert matrix.empty


class TestFilterByProject:
    """Test filtering aggregated data by project."""

    def test_filter_by_project(self, calculator):
        """Test filtering entries by project code."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        billing_results = [
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("637.50"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("637.50"),
                total_cost=Decimal("450.00"),
                profit=Decimal("187.50"),
                profit_margin_percentage=Decimal("29.41"),
            )
            for _ in range(2)
        ]

        data = AggregatedTimesheetData(
            entries=entries, billing_results=billing_results, trips=[]
        )

        filtered = calculator.filter_by_project(data, "PROJ-001")

        assert len(filtered.entries) == 1
        assert filtered.entries[0].project_code == "PROJ-001"
        assert filtered.entries[0].freelancer_name == "John Doe"


class TestFilterByDateRange:
    """Test filtering aggregated data by date range."""

    def test_filter_by_date_range(self, calculator):
        """Test filtering entries by date range."""
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 10),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2023, 6, 20),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]

        billing_results = [
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("637.50"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("637.50"),
                total_cost=Decimal("450.00"),
                profit=Decimal("187.50"),
                profit_margin_percentage=Decimal("29.41"),
            )
            for _ in range(3)
        ]

        data = AggregatedTimesheetData(
            entries=entries, billing_results=billing_results, trips=[]
        )

        filtered = calculator.filter_by_date_range(
            data, start_date=dt.date(2023, 6, 12), end_date=dt.date(2023, 6, 18)
        )

        assert len(filtered.entries) == 1
        assert filtered.entries[0].date == dt.date(2023, 6, 15)


class TestGetWeekRange:
    """Test getting weekly data for specific week range."""

    def test_get_week_range(self, calculator):
        """Test extracting data for specific week range."""
        weekly_data = [
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=20,
                billable_hours=Decimal("40.0"),
                work_hours=Decimal("45.0"),
                entries_count=5,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=21,
                billable_hours=Decimal("32.0"),
                work_hours=Decimal("36.0"),
                entries_count=4,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=22,
                billable_hours=Decimal("38.0"),
                work_hours=Decimal("42.0"),
                entries_count=5,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=23,
                billable_hours=Decimal("35.0"),
                work_hours=Decimal("40.0"),
                entries_count=5,
            ),
        ]

        result = calculator.get_week_range(weekly_data, 2023, 21, 22)

        assert len(result) == 2
        assert all(r.week_number >= 21 and r.week_number <= 22 for r in result)
        assert all(r.year == 2023 for r in result)

    def test_get_week_range_year_boundary(self, calculator):
        """Test week range extraction across year boundary."""
        weekly_data = [
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2023,
                week_number=52,
                billable_hours=Decimal("40.0"),
                work_hours=Decimal("45.0"),
                entries_count=5,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2024,
                week_number=1,
                billable_hours=Decimal("32.0"),
                work_hours=Decimal("36.0"),
                entries_count=4,
            ),
            WeeklyHoursData(
                freelancer_name="John Doe",
                year=2024,
                week_number=2,
                billable_hours=Decimal("38.0"),
                work_hours=Decimal("42.0"),
                entries_count=5,
            ),
        ]

        # Get weeks from 2023-W52 to 2024-W01 (need to handle differently)
        result_2023 = calculator.get_week_range(weekly_data, 2023, 52, 52)
        result_2024 = calculator.get_week_range(weekly_data, 2024, 1, 1)

        assert len(result_2023) == 1
        assert result_2023[0].year == 2023
        assert result_2023[0].week_number == 52

        assert len(result_2024) == 1
        assert result_2024[0].year == 2024
        assert result_2024[0].week_number == 1
