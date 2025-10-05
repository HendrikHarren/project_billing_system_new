"""Generate complete master timesheet with all 4 sheets.

This script demonstrates the complete end-to-end workflow:
1. Read master timesheet data
2. Generate pivot tables
3. Write all 4 sheets to Google Sheets
4. Apply formatting
"""

import pandas as pd
from dotenv import load_dotenv

from src.google_auth import get_drive_service, get_sheets_service
from src.writers import GoogleSheetsWriter, MasterTimesheetData, PivotTableGenerator


def main():
    """Generate complete master timesheet output."""
    load_dotenv()

    print("=" * 80)
    print("COMPLETE MASTER TIMESHEET GENERATION")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing Google API services...")
    sheets_api = get_sheets_service()
    drive_api = get_drive_service()

    # Read existing data for demo
    print("2. Reading sample data from existing master timesheet...")
    existing_file_id = "1c-CT8YuptId0g80JAfmoqYueu_jZuWoPt7_jN9PjKyU"

    # Read Timesheet_master
    result = (
        sheets_api.spreadsheets()
        .values()
        .get(spreadsheetId=existing_file_id, range="Timesheet_master!A1:X1000")
        .execute()
    )
    values = result.get("values", [])

    if len(values) > 1:
        headers = values[0]
        data_rows = values[1:]
        timesheet_master = pd.DataFrame(data_rows, columns=headers)
        print(f"   ✓ Read {len(timesheet_master)} rows for Timesheet_master")
    else:
        print("   ⚠ No data found")
        return

    # Read Trips_master
    result = (
        sheets_api.spreadsheets()
        .values()
        .get(spreadsheetId=existing_file_id, range="Trips_master!A1:G100")
        .execute()
    )
    values = result.get("values", [])

    if len(values) > 1:
        headers = values[0]
        data_rows = values[1:]
        trips_master = pd.DataFrame(data_rows, columns=headers)
        print(f"   ✓ Read {len(trips_master)} rows for Trips_master")
    else:
        trips_master = pd.DataFrame(
            columns=[
                "Name",
                "Project",
                "Location",
                "Trip Start Date",
                "Trip Duration",
                "Trip Reimbursement",
                "Month",
            ]
        )
        print("   ✓ No trips data, using empty DataFrame")

    # Create MasterTimesheetData
    master_data = MasterTimesheetData(
        timesheet_master=timesheet_master, trips_master=trips_master
    )

    # Generate pivot tables
    print("\n3. Generating pivot tables...")
    pivot_generator = PivotTableGenerator(timesheet_master)

    # Auto-detect filters from data
    # Use the most recent year and month
    timesheet_master["Year"] = pd.to_numeric(timesheet_master["Year"], errors="coerce")
    timesheet_master["Month"] = pd.to_numeric(
        timesheet_master["Month"], errors="coerce"
    )

    most_recent_year = int(timesheet_master["Year"].max())
    most_recent_month = int(
        timesheet_master[timesheet_master["Year"] == most_recent_year]["Month"].max()
    )
    most_common_project = timesheet_master["Project"].mode()[0]

    print(
        f"   Using filters: Project={most_common_project}, "
        f"Year={most_recent_year}, Month={most_recent_month}"
    )

    pivot_data = pivot_generator.generate(
        project_filter=most_common_project,
        year_filter=most_recent_year,
        month_filter=most_recent_month,
    )

    print(f"   ✓ Pivot_master: {len(pivot_data.pivot_master)} rows")
    print(f"   ✓ Weekly_reporting: {len(pivot_data.weekly_reporting)} rows")

    # Write to Google Sheets
    print("\n4. Creating Google Sheets file with all 4 sheets...")
    writer = GoogleSheetsWriter(sheets_api, drive_api)

    output_folder_id = "1z2lA8w5VQgKg-_qJsTqwd0Rowicf7S_9"

    file_id, url = writer.write_master_timesheet(
        master_data=master_data,
        pivot_data=pivot_data,
        output_folder_id=output_folder_id,
    )

    print("\n" + "=" * 80)
    print("✅ SUCCESS - ALL 4 SHEETS GENERATED!")
    print("=" * 80)
    print("\nGoogle Sheets URL:")
    print(url)
    print("\nContents:")
    print(f"  1. Timesheet_master: {len(master_data.timesheet_master)} rows")
    print(f"  2. Trips_master: {len(master_data.trips_master)} rows")
    print(f"  3. Pivot_master: {len(pivot_data.pivot_master)} rows")
    print(f"  4. Weekly_reporting: {len(pivot_data.weekly_reporting)} rows")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
