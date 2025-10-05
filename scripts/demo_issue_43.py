#!/usr/bin/env python3
"""Demo script for Issue #43: Configurable Date Range Filtering.

This script demonstrates the new date range filtering capability in
TimesheetAggregator for improved performance when processing large datasets.

Before: Read all entries → Calculate all → Filter
After:  Read all entries → Filter → Calculate only filtered (faster!)

Run this script to see the performance difference and filtering behavior.
"""

import datetime as dt
from decimal import Decimal
from unittest.mock import MagicMock

from src.aggregators.timesheet_aggregator import TimesheetAggregator
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


def create_sample_entries():
    """Create sample timesheet entries spanning multiple months."""
    entries = []

    # May 2023 entries
    for day in [15, 20, 25]:
        entries.append(
            TimesheetEntry(
                freelancer_name="Alice Johnson",
                date=dt.date(2023, 5, day),
                project_code="PROJECT_A",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )
        )

    # June 2023 entries
    for day in [1, 5, 10, 15, 20, 25, 30]:
        entries.append(
            TimesheetEntry(
                freelancer_name="Alice Johnson",
                date=dt.date(2023, 6, day),
                project_code="PROJECT_A",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=60,
                location="onsite",
            )
        )

    # July 2023 entries
    for day in [5, 10]:
        entries.append(
            TimesheetEntry(
                freelancer_name="Alice Johnson",
                date=dt.date(2023, 7, day),
                project_code="PROJECT_A",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )
        )

    return entries


def create_mock_services(entries):
    """Create mock services for testing."""
    # Mock Drive service
    mock_drive = MagicMock()
    mock_drive.list_files_in_folder.return_value = [
        {"id": "file1", "name": "Alice_Johnson_Timesheet"}
    ]

    # Mock Timesheet reader
    mock_reader = MagicMock()
    mock_reader.read_timesheet.return_value = entries

    # Mock Project Terms reader
    mock_terms = MagicMock()
    terms_map = {
        ("Alice Johnson", "PROJECT_A"): ProjectTerms(
            freelancer_name="Alice Johnson",
            project_code="PROJECT_A",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )
    }
    mock_terms.get_all_project_terms.return_value = terms_map

    return mock_reader, mock_terms, mock_drive


def demo_no_filtering():
    """Demo 1: No filtering (read all data)."""
    print("=" * 70)
    print("DEMO 1: No Filtering (Baseline)")
    print("=" * 70)

    entries = create_sample_entries()
    mock_reader, mock_terms, mock_drive = create_mock_services(entries)

    aggregator = TimesheetAggregator(mock_reader, mock_terms, mock_drive)

    result = aggregator.aggregate_timesheets("folder-id")

    print(f"\n📊 Total entries read: {len(entries)}")
    print(f"✅ Entries processed: {len(result.entries)}")
    print(f"💰 Billing calculated for: {len(result.billing_results)} entries")
    print(f"✈️  Trips identified: {len(result.trips)}")
    print("\n💡 Note: All entries were processed for billing calculation\n")


def demo_date_range_filtering():
    """Demo 2: Date range filtering (June only)."""
    print("=" * 70)
    print("DEMO 2: Date Range Filtering (June 2023)")
    print("=" * 70)

    entries = create_sample_entries()
    mock_reader, mock_terms, mock_drive = create_mock_services(entries)

    aggregator = TimesheetAggregator(mock_reader, mock_terms, mock_drive)

    # Filter for June 2023 only
    result = aggregator.aggregate_timesheets(
        "folder-id", start_date=dt.date(2023, 6, 1), end_date=dt.date(2023, 6, 30)
    )

    print(f"\n📊 Total entries read: {len(entries)}")
    print("🔍 Date filter: 2023-06-01 to 2023-06-30")
    print(f"✅ Entries after filtering: {len(result.entries)}")
    print(f"💰 Billing calculated for: {len(result.billing_results)} entries")
    print(f"✈️  Trips identified: {len(result.trips)}")
    print(
        f"\n⚡ Performance: Only {len(result.entries)}/{len(entries)} entries "
        f"processed for billing"
    )
    print(
        f"   Reduction: {100 - (len(result.entries) / len(entries) * 100):.1f}% "
        f"fewer calculations\n"
    )


def demo_combined_filtering():
    """Demo 3: Combined filters (date range + project + freelancer)."""
    print("=" * 70)
    print("DEMO 3: Combined Filtering")
    print("=" * 70)

    entries = create_sample_entries()

    # Add entries for another freelancer
    for day in [1, 5, 10]:
        entries.append(
            TimesheetEntry(
                freelancer_name="Bob Smith",
                date=dt.date(2023, 6, day),
                project_code="PROJECT_B",
                start_time=dt.time(10, 0),
                end_time=dt.time(18, 0),
                break_minutes=60,
                travel_time_minutes=0,
                location="remote",
            )
        )

    mock_reader, mock_terms, mock_drive = create_mock_services(entries)

    # Add terms for Bob
    terms_map = mock_terms.get_all_project_terms.return_value
    terms_map[("Bob Smith", "PROJECT_B")] = ProjectTerms(
        freelancer_name="Bob Smith",
        project_code="PROJECT_B",
        hourly_rate=Decimal("90.00"),
        travel_surcharge_percentage=Decimal("20.0"),
        travel_time_percentage=Decimal("50.0"),
        cost_per_hour=Decimal("65.00"),
    )

    aggregator = TimesheetAggregator(mock_reader, mock_terms, mock_drive)

    # Filter: June 2023 + PROJECT_A + Alice Johnson
    result = aggregator.aggregate_timesheets(
        "folder-id",
        start_date=dt.date(2023, 6, 1),
        end_date=dt.date(2023, 6, 30),
        project_code="PROJECT_A",
        freelancer_name="Alice Johnson",
    )

    print(f"\n📊 Total entries read: {len(entries)}")
    print("🔍 Filters applied:")
    print("   - Date: 2023-06-01 to 2023-06-30")
    print("   - Project: PROJECT_A")
    print("   - Freelancer: Alice Johnson")
    print(f"✅ Entries after filtering: {len(result.entries)}")
    print(f"💰 Billing calculated for: {len(result.billing_results)} entries")
    print(f"✈️  Trips identified: {len(result.trips)}")
    print(
        f"\n⚡ Performance: Only {len(result.entries)}/{len(entries)} entries "
        f"processed for billing"
    )
    print(
        f"   Reduction: {100 - (len(result.entries) / len(entries) * 100):.1f}% "
        f"fewer calculations\n"
    )


def demo_real_world_scenario():
    """Demo 4: Real-world scenario with 30 freelancers."""
    print("=" * 70)
    print("DEMO 4: Real-World Scenario (30 Freelancers, Full Year)")
    print("=" * 70)

    # Simulate 30 freelancers with 10 entries each per month for a year
    total_freelancers = 30
    entries_per_month = 10
    months_in_year = 12

    total_entries = total_freelancers * entries_per_month * months_in_year
    entries_per_month_all_freelancers = total_freelancers * entries_per_month

    print("\n📊 Scenario:")
    print(f"   - Freelancers: {total_freelancers}")
    print(f"   - Entries per freelancer per month: {entries_per_month}")
    print(f"   - Total entries in system: {total_entries}")

    print("\n❌ WITHOUT Date Filtering:")
    print(f"   - Entries processed: {total_entries}")
    print(f"   - Billing calculations: {total_entries}")

    print("\n✅ WITH Date Filtering (Single Month):")
    print(f"   - Entries processed: {entries_per_month_all_freelancers}")
    print(f"   - Billing calculations: {entries_per_month_all_freelancers}")
    reduction = 100 - (entries_per_month_all_freelancers / total_entries * 100)
    print(f"   - Reduction: {reduction:.1f}% fewer calculations")
    print(f"   - Performance: ~{months_in_year}x faster for monthly reports")

    print("\n💡 Key Takeaway:")
    print("   For monthly reports, date filtering reduces processing time")
    print("   significantly by avoiding unnecessary calculations on 11 months")
    print("   of data you don't need!\n")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Issue #43: Configurable Date Range Filtering Demo".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Run demos
    demo_no_filtering()
    demo_date_range_filtering()
    demo_combined_filtering()
    demo_real_world_scenario()

    print("=" * 70)
    print("✨ Demo Complete!")
    print("=" * 70)
    print()
    print("🚀 Try it yourself:")
    print("   python -m src.cli generate-report --month 2024-06")
    print()


if __name__ == "__main__":
    main()
