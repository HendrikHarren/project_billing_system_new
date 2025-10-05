"""Generate a test master timesheet output to Google Sheets.

This script uses REAL data to show what the current implementation produces.
"""

from datetime import datetime

from demo_master_timesheet import generate_timesheet_master_dataframe
from dotenv import load_dotenv

from src.google_auth import get_drive_service, get_sheets_service


def write_dataframe_to_sheet(sheets_service, df, spreadsheet_id, sheet_name):
    """Write DataFrame to Google Sheet."""
    # Convert DataFrame to list of lists
    values = [df.columns.tolist()] + df.values.tolist()

    # Write to sheet
    range_name = f"{sheet_name}!A1"
    body = {"values": values}

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


def main():
    """Generate test output with real data."""
    load_dotenv()

    print("=" * 80)
    print("GENERATING TEST MASTER TIMESHEET OUTPUT")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing services...")
    sheets_api = get_sheets_service()
    drive_api = get_drive_service()

    # For now, use the analyze_outputs.py approach to get real data
    print("2. Reading real aggregated data from existing output...")
    # Use the most recent master timesheet as a reference
    existing_file_id = "1c-CT8YuptId0g80JAfmoqYueu_jZuWoPt7_jN9PjKyU"

    result = (
        sheets_api.spreadsheets()
        .values()
        .get(spreadsheetId=existing_file_id, range="Timesheet_master!A1:X100")
        .execute()
    )
    values = result.get("values", [])

    print(f"   ✓ Read {len(values)-1} rows from existing master timesheet")

    # Convert to DataFrame
    import pandas as pd

    if len(values) > 1:
        headers = values[0]
        data_rows = values[1:]
        master_df = pd.DataFrame(data_rows, columns=headers)
    else:
        print("   ⚠ No data found, using sample")
        import datetime as dt
        from decimal import Decimal

        from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
        from src.calculators.billing_calculator import BillingResult
        from src.models.timesheet import TimesheetEntry

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
        master_df = generate_timesheet_master_dataframe(aggregated_data)

    print(
        f"   ✓ DataFrame ready: {len(master_df)} rows × "
        f"{len(master_df.columns)} columns"
    )

    # Create new spreadsheet
    print("\n3. Creating Google Sheets output...")
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    spreadsheet_title = f"TEST_Timesheet_Master_{timestamp}"

    spreadsheet = {
        "properties": {"title": spreadsheet_title},
        "sheets": [{"properties": {"sheetId": 0, "title": "Timesheet_master"}}],
    }

    spreadsheet = sheets_api.spreadsheets().create(body=spreadsheet).execute()
    file_id = spreadsheet.get("spreadsheetId")

    print(f"   ✓ Created spreadsheet: {spreadsheet_title}")

    # Write data
    print("4. Writing data to sheet...")
    write_dataframe_to_sheet(sheets_api, master_df, file_id, "Timesheet_master")
    print(f"   ✓ Wrote {len(master_df)} rows")

    # Move to output folder
    print("\n5. Moving to output folder...")
    output_folder_id = "1z2lA8w5VQgKg-_qJsTqwd0Rowicf7S_9"

    file = drive_api.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents"))

    drive_api.files().update(
        fileId=file_id,
        addParents=output_folder_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()

    # Generate URL
    url = f"https://docs.google.com/spreadsheets/d/{file_id}"

    print("\n" + "=" * 80)
    print("✅ SUCCESS!")
    print("=" * 80)
    print(f"\nSpreadsheet: {spreadsheet_title}")
    print(f"URL: {url}")
    print(f"\nRows: {len(master_df)}")
    print(f"Columns: {len(master_df.columns)}")
    print(f"Date Range: {master_df['Date'].min()} to {master_df['Date'].max()}")
    print(f"Freelancers: {master_df['Name'].nunique()}")
    print(f"Projects: {master_df['Project'].nunique()}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
