"""Unit tests for MasterTimesheetGenerator."""

import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
from src.calculators.billing_calculator import BillingResult
from src.models.timesheet import TimesheetEntry
from src.models.trip import Trip
from src.writers.master_timesheet_generator import (
    MasterTimesheetData,
    MasterTimesheetGenerator,
)


@pytest.fixture
def sample_timesheet_entries():
    """Create sample timesheet entries for testing."""
    return [
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2023, 6, 15),
            project_code="P&C_NEWRETAIL",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=60,
            travel_time_minutes=0,
            location="remote",
            notes="Development work",
        ),
        TimesheetEntry(
            freelancer_name="Jane Smith",
            date=dt.date(2023, 6, 16),
            project_code="HILTI",
            start_time=dt.time(8, 0),
            end_time=dt.time(18, 30),
            break_minutes=30,
            travel_time_minutes=240,
            location="onsite",
            notes="On-site consultation",
        ),
    ]


@pytest.fixture
def sample_billing_results():
    """Create sample billing results for testing."""
    return [
        BillingResult(
            billable_hours=Decimal("7.0"),
            work_hours=Decimal("8.0"),
            break_hours=Decimal("1.0"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("1050.00"),
            travel_surcharge=Decimal("0.0"),
            total_billed=Decimal("1050.00"),
            total_cost=Decimal("700.00"),
            profit=Decimal("350.00"),
            profit_margin_percentage=Decimal("33.33"),
        ),
        BillingResult(
            billable_hours=Decimal("12.0"),
            work_hours=Decimal("10.5"),
            break_hours=Decimal("0.5"),
            travel_hours=Decimal("2.0"),
            hours_billed=Decimal("2100.00"),
            travel_surcharge=Decimal("262.50"),
            total_billed=Decimal("2362.50"),
            total_cost=Decimal("1380.00"),
            profit=Decimal("982.50"),
            profit_margin_percentage=Decimal("41.58"),
        ),
    ]


@pytest.fixture
def sample_trips():
    """Create sample trips for testing."""
    return [
        Trip(
            freelancer_name="Jane Smith",
            project_code="HILTI",
            location="onsite",
            start_date=dt.date(2023, 6, 16),
            end_date=dt.date(2023, 6, 17),
            duration_days=2,
        ),
    ]


@pytest.fixture
def aggregated_data(sample_timesheet_entries, sample_billing_results, sample_trips):
    """Create aggregated timesheet data for testing."""
    return AggregatedTimesheetData(
        entries=sample_timesheet_entries,
        billing_results=sample_billing_results,
        trips=sample_trips,
    )


class TestMasterTimesheetGenerator:
    """Test suite for MasterTimesheetGenerator."""

    def test_initialization(self, aggregated_data):
        """Test generator initialization."""
        generator = MasterTimesheetGenerator(aggregated_data)
        assert generator.aggregated_data == aggregated_data

    def test_generate_returns_master_timesheet_data(self, aggregated_data):
        """Test that generate returns MasterTimesheetData object."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert isinstance(result, MasterTimesheetData)
        assert isinstance(result.timesheet_master, pd.DataFrame)
        assert isinstance(result.trips_master, pd.DataFrame)

    def test_timesheet_master_has_24_columns(self, aggregated_data):
        """Test that timesheet_master has exactly 24 columns."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert len(result.timesheet_master.columns) == 24

    def test_timesheet_master_column_order(self, aggregated_data):
        """Test that columns are in the correct order."""
        expected_columns = [
            "Name",
            "Date",
            "Project",
            "Location",
            "Start Time",
            "End Time",
            "Topics worked on",
            "Break",
            "Travel time",
            "Trip Start Date",
            "Trip Duration",
            "Rate",
            "Cost",
            "Share of travel as work",
            "surcharge for travel",
            "Hours",
            "Hours billed",
            "Hours cost",
            "Travel hours billed",
            "Travel surcharge billed",
            "Travel surcharge cost",
            "Year",
            "Month",
            "Week",
        ]

        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert list(result.timesheet_master.columns) == expected_columns

    def test_timesheet_master_row_count(self, aggregated_data):
        """Test that timesheet_master has correct number of rows."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert len(result.timesheet_master) == len(aggregated_data.entries)

    def test_date_formatting(self, aggregated_data):
        """Test that dates are formatted as YYYY-MM-DD strings."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert result.timesheet_master["Date"].iloc[0] == "2023-06-15"
        assert result.timesheet_master["Date"].iloc[1] == "2023-06-16"

    def test_time_formatting(self, aggregated_data):
        """Test that times are formatted as HH:MM strings."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert result.timesheet_master["Start Time"].iloc[0] == "09:00"
        assert result.timesheet_master["End Time"].iloc[0] == "17:00"
        assert result.timesheet_master["Start Time"].iloc[1] == "08:00"
        assert result.timesheet_master["End Time"].iloc[1] == "18:30"

    def test_break_time_formatting(self, aggregated_data):
        """Test that break time is formatted as HH:MM string."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert result.timesheet_master["Break"].iloc[0] == "01:00"
        assert result.timesheet_master["Break"].iloc[1] == "00:30"

    def test_travel_time_formatting(self, aggregated_data):
        """Test that travel time is formatted as HH:MM string."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert result.timesheet_master["Travel time"].iloc[0] == "00:00"
        assert result.timesheet_master["Travel time"].iloc[1] == "04:00"

    def test_year_month_week_extraction(self, aggregated_data):
        """Test that Year, Month, Week are extracted correctly."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        # First entry: 2023-06-15
        assert result.timesheet_master["Year"].iloc[0] == 2023
        assert result.timesheet_master["Month"].iloc[0] == 6
        assert result.timesheet_master["Week"].iloc[0] == 24  # ISO week

        # Second entry: 2023-06-16
        assert result.timesheet_master["Year"].iloc[1] == 2023
        assert result.timesheet_master["Month"].iloc[1] == 6
        assert result.timesheet_master["Week"].iloc[1] == 24

    def test_billing_data_from_results(self, aggregated_data):
        """Test that billing data comes from BillingResult objects."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        # First entry
        assert result.timesheet_master["Hours"].iloc[0] == 7.0
        assert result.timesheet_master["Hours billed"].iloc[0] == 1050.00
        assert result.timesheet_master["Hours cost"].iloc[0] == 700.00

        # Second entry
        assert result.timesheet_master["Hours"].iloc[1] == 12.0
        assert result.timesheet_master["Hours billed"].iloc[1] == 2100.00
        assert result.timesheet_master["Hours cost"].iloc[1] == 1380.00

    def test_travel_surcharge_data(self, aggregated_data):
        """Test that travel surcharge data is included correctly."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        # First entry (remote, no travel surcharge)
        assert result.timesheet_master["Travel hours billed"].iloc[0] == 0.0
        assert result.timesheet_master["Travel surcharge billed"].iloc[0] == 0.0
        assert result.timesheet_master["Travel surcharge cost"].iloc[0] == 0.0

        # Second entry (onsite, has travel surcharge)
        assert result.timesheet_master["Travel hours billed"].iloc[1] == 10.0
        assert result.timesheet_master["Travel surcharge billed"].iloc[1] == 262.50
        assert result.timesheet_master["Travel surcharge cost"].iloc[1] == 172.50

    def test_trip_data_merging(self, aggregated_data):
        """Test that trip data is merged correctly."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        # First entry (no trip)
        assert result.timesheet_master["Trip Start Date"].iloc[0] == ""
        assert result.timesheet_master["Trip Duration"].iloc[0] == 0

        # Second entry (has trip)
        assert result.timesheet_master["Trip Start Date"].iloc[1] == "2023-06-16"
        assert result.timesheet_master["Trip Duration"].iloc[1] == 2

    def test_trips_master_has_7_columns(self, aggregated_data):
        """Test that trips_master has exactly 7 columns."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert len(result.trips_master.columns) == 7

    def test_trips_master_column_order(self, aggregated_data):
        """Test that trips_master columns are in correct order."""
        expected_columns = [
            "Name",
            "Project",
            "Location",
            "Trip Start Date",
            "Trip Duration",
            "Trip Reimbursement",
            "Month",
        ]

        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        assert list(result.trips_master.columns) == expected_columns

    def test_empty_entries_handling(self):
        """Test handling of empty timesheet entries."""
        empty_data = AggregatedTimesheetData(entries=[], billing_results=[], trips=[])

        generator = MasterTimesheetGenerator(empty_data)
        result = generator.generate()

        assert len(result.timesheet_master) == 0
        assert len(result.trips_master) == 0
        assert len(result.timesheet_master.columns) == 24
        assert len(result.trips_master.columns) == 7

    def test_large_dataset_performance(self):
        """Test performance with large dataset (9000+ rows)."""
        # Create 9000 entries
        large_entries = []
        large_billing = []

        for i in range(9000):
            large_entries.append(
                TimesheetEntry(
                    freelancer_name=f"Freelancer {i % 30}",
                    date=dt.date(2023, 1, 1) + dt.timedelta(days=i % 365),
                    project_code="TEST_PROJECT",
                    start_time=dt.time(9, 0),
                    end_time=dt.time(17, 0),
                    break_minutes=60,
                    travel_time_minutes=0,
                    location="remote",
                    notes="Test work",
                )
            )
            large_billing.append(
                BillingResult(
                    work_hours=Decimal("8.0"),
                    break_hours=Decimal("1.0"),
                    travel_hours=Decimal("0.0"),
                    total_hours=Decimal("7.0"),
                    hourly_rate=Decimal("150.00"),
                    cost_per_hour=Decimal("100.00"),
                    revenue=Decimal("1050.00"),
                    cost=Decimal("700.00"),
                    profit=Decimal("350.00"),
                    profit_margin=Decimal("33.33"),
                    travel_surcharge_hours=Decimal("0.0"),
                    travel_surcharge_revenue=Decimal("0.0"),
                    travel_surcharge_cost=Decimal("0.0"),
                )
            )

        large_data = AggregatedTimesheetData(
            entries=large_entries, billing_results=large_billing, trips=[]
        )

        generator = MasterTimesheetGenerator(large_data)
        result = generator.generate()

        assert len(result.timesheet_master) == 9000
        assert len(result.timesheet_master.columns) == 24

    def test_location_formatting(self, aggregated_data):
        """Test that location values are properly formatted."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        # Check that locations match expected format
        assert result.timesheet_master["Location"].iloc[0] in [
            "Off-site",
            "On-site",
            "remote",
            "onsite",
        ]

    def test_all_data_types_are_correct(self, aggregated_data):
        """Test that all columns have appropriate data types."""
        generator = MasterTimesheetGenerator(aggregated_data)
        result = generator.generate()

        df = result.timesheet_master

        # String columns
        assert df["Name"].dtype == object
        assert df["Date"].dtype == object  # Formatted as string
        assert df["Project"].dtype == object
        assert df["Location"].dtype == object
        assert df["Start Time"].dtype == object  # Formatted as string
        assert df["End Time"].dtype == object  # Formatted as string
        assert df["Topics worked on"].dtype == object
        assert df["Break"].dtype == object  # Formatted as string
        assert df["Travel time"].dtype == object  # Formatted as string
        assert df["Trip Start Date"].dtype == object  # Formatted as string

        # Numeric columns
        assert df["Trip Duration"].dtype in [int, "int64", "int32"]
        assert df["Year"].dtype in [int, "int64", "int32"]
        assert df["Month"].dtype in [int, "int64", "int32"]
        assert df["Week"].dtype in [int, "int64", "int32"]

        # Float columns (hours and currency)
        assert df["Hours"].dtype in [float, "float64"]
        assert df["Hours billed"].dtype in [float, "float64"]
        assert df["Hours cost"].dtype in [float, "float64"]
