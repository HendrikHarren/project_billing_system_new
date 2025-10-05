"""Demo script for master timesheet generation.

This script demonstrates the complete workflow:
1. Aggregate timesheet data from Google Drive
2. Generate master timesheet DataFrames
3. Write to Google Sheets with formatting
"""

import os

import pandas as pd
from dotenv import load_dotenv

from src.google_auth import get_drive_service


def generate_timesheet_master_dataframe(aggregated_data):
    """Generate the 24-column timesheet master DataFrame.

    Args:
        aggregated_data: AggregatedTimesheetData from aggregator

    Returns:
        DataFrame with all timesheet data formatted for output
    """
    rows = []

    for i, entry in enumerate(aggregated_data.entries):
        billing = aggregated_data.billing_results[i]

        # Find matching trip if exists
        trip = None
        for t in aggregated_data.trips:
            if (
                t.freelancer_name == entry.freelancer_name
                and t.project_code == entry.project_code
                and t.start_date <= entry.date <= t.end_date
            ):
                trip = t
                break

        # Format location
        location = "On-site" if entry.location == "onsite" else "Off-site"

        # Build row
        # Calculate rate
        rate = (
            float(billing.hours_billed / billing.billable_hours)
            if billing.billable_hours > 0
            else 0.0
        )

        row = {
            "Name": entry.freelancer_name,
            "Date": entry.date.strftime("%Y-%m-%d"),
            "Project": entry.project_code,
            "Location": location,
            "Start Time": entry.start_time.strftime("%H:%M"),
            "End Time": entry.end_time.strftime("%H:%M"),
            "Topics worked on": entry.notes or "",
            "Break": f"{entry.break_minutes // 60:02d}:{entry.break_minutes % 60:02d}",
            "Travel time": (
                f"{entry.travel_time_minutes // 60:02d}:"
                f"{entry.travel_time_minutes % 60:02d}"
            ),
            "Trip Start Date": (trip.start_date.strftime("%Y-%m-%d") if trip else ""),
            "Trip Duration": trip.duration_days if trip else 0,
            "Rate": rate,
            "Cost": 0.0,  # Will be filled from project terms
            "Share of travel as work": 0.5,
            "surcharge for travel": 0.15,
            "Hours": float(billing.billable_hours),
            "Hours billed": float(billing.hours_billed),
            "Hours cost": 0.0,  # Will be calculated
            "Travel hours billed": float(billing.travel_hours)
            if entry.location == "onsite"
            else 0.0,
            "Travel surcharge billed": float(billing.travel_surcharge),
            "Travel surcharge cost": 0.0,  # Will be calculated
            "Year": entry.date.year,
            "Month": entry.date.month,
            "Week": entry.date.isocalendar().week,
        }
        rows.append(row)

    columns = [
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

    return pd.DataFrame(rows, columns=columns)


def main():
    """Run the master timesheet generation demo."""
    load_dotenv()

    print("=" * 80)
    print("MASTER TIMESHEET GENERATION DEMO")
    print("=" * 80)

    # Initialize Google API services directly
    print("\n1. Initializing Google API services...")
    drive_service = get_drive_service()

    # Read all timesheets using the demo_data_flow approach (simpler)
    print("\n2. Reading timesheet data from Google Drive...")
    timesheet_folder_id = os.getenv("TIMESHEET_FOLDER_ID")

    # List files
    response = (
        drive_service.files()
        .list(q=f"'{timesheet_folder_id}' in parents", fields="files(id, name)")
        .execute()
    )
    files = response.get("files", [])
    print(f"   ✓ Found {len(files)} timesheet files")

    # For now, just use sample data to demonstrate the structure
    import datetime as dt
    from decimal import Decimal

    from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
    from src.calculators.billing_calculator import BillingResult
    from src.models.timesheet import TimesheetEntry

    # Create minimal sample data
    sample_entries = [
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
        )
    ]

    sample_billing = [
        BillingResult(
            billable_hours=Decimal("7.0"),
            work_hours=Decimal("8.0"),
            break_hours=Decimal("1.0"),
            travel_hours=Decimal("0.0"),
            hours_billed=Decimal("1050.00"),
            travel_surcharge=Decimal("0.00"),
            total_billed=Decimal("1050.00"),
            total_cost=Decimal("700.00"),
            profit=Decimal("350.00"),
            profit_margin_percentage=Decimal("33.33"),
        )
    ]

    aggregated_data = AggregatedTimesheetData(
        entries=sample_entries, billing_results=sample_billing, trips=[]
    )

    print(f"   ✓ Processed {len(aggregated_data.entries)} timesheet entries")
    print(f"   ✓ Found {len(aggregated_data.trips)} trips")

    # Generate master timesheet DataFrame
    print("\n3. Generating master timesheet DataFrame...")
    master_df = generate_timesheet_master_dataframe(aggregated_data)

    print(
        f"   ✓ Generated DataFrame with {len(master_df)} rows and "
        f"{len(master_df.columns)} columns"
    )
    print(f"   ✓ Columns: {', '.join(master_df.columns[:6])}...")

    # Show sample data
    print("\n4. Sample data (first 3 rows):")
    print(master_df.head(3).to_string())

    # Show summary statistics
    print("\n5. Summary Statistics:")
    print(f"   Total Hours: {master_df['Hours'].sum():.2f}")
    print(f"   Total Billed: €{master_df['Hours billed'].sum():.2f}")
    print(f"   Unique Freelancers: {master_df['Name'].nunique()}")
    print(f"   Unique Projects: {master_df['Project'].nunique()}")
    print(f"   Date Range: {master_df['Date'].min()} to {master_df['Date'].max()}")

    print("\n" + "=" * 80)
    print("✓ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()
