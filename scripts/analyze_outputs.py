"""
Script to analyze output files in the Monthly Invoicing folder.
This will help us understand the expected output structure.
"""
import os

from dotenv import load_dotenv

from src.google_auth import get_drive_service, get_sheets_service


def analyze_monthly_invoicing_folder():
    """Analyze files in the Monthly Invoicing folder."""
    print("Analyzing Monthly Invoicing folder...")

    try:
        drive_service = get_drive_service()
        monthly_folder_id = os.getenv("MONTHLY_INVOICING_FOLDER_ID")

        print(f"Listing files in Monthly Invoicing folder: {monthly_folder_id}")

        # List files in the monthly invoicing folder
        response = (
            drive_service.files()
            .list(
                q=f"'{monthly_folder_id}' in parents",
                fields="files(id, name, modifiedTime, mimeType)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        files = response.get("files", [])
        print(f"Found {len(files)} files:")

        # Group files by type
        spreadsheets = []
        other_files = []

        for file in files:
            print(
                f"  - {file['name']} (ID: {file['id']}, "
                f"Modified: {file['modifiedTime']}, Type: {file['mimeType']})"
            )
            if file["mimeType"] == "application/vnd.google-apps.spreadsheet":
                spreadsheets.append(file)
            else:
                other_files.append(file)

        print(
            f"\nFound {len(spreadsheets)} spreadsheets and "
            f"{len(other_files)} other files"
        )
        return spreadsheets

    except Exception as e:
        print(f"Error accessing Monthly Invoicing folder: {e}")
        return []


def analyze_master_timesheet(file_id: str, file_name: str):
    """Analyze a master timesheet file structure."""
    print(f"\n=== Analyzing: {file_name} ===")

    try:
        sheets_service = get_sheets_service()

        # Get spreadsheet properties to see all sheets
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
        sheets = spreadsheet.get("sheets", [])

        print(f"Found {len(sheets)} sheets:")
        for sheet in sheets:
            sheet_title = sheet["properties"]["title"]
            print(f"  - {sheet_title}")

        # Analyze each sheet
        for sheet in sheets:
            sheet_title = sheet["properties"]["title"]
            print(f"\n--- Sheet: {sheet_title} ---")

            try:
                # Read first few rows to understand structure
                result = (
                    sheets_service.spreadsheets()
                    .values()
                    .get(spreadsheetId=file_id, range=f"{sheet_title}!A1:Z10")
                    .execute()
                )

                values = result.get("values", [])
                print(f"Rows in sample: {len(values)}")

                if values:
                    print(
                        "Headers/First row:",
                        values[0] if len(values) > 0 else "No data",
                    )
                    if len(values) > 1:
                        print("Second row:", values[1])
                    if len(values) > 2:
                        print("Third row:", values[2])

                # Get sheet dimensions
                if "gridProperties" in sheet["properties"]:
                    props = sheet["properties"]["gridProperties"]
                    rows = props.get("rowCount", "Unknown")
                    cols = props.get("columnCount", "Unknown")
                    print(f"Sheet dimensions: {rows} rows x {cols} columns")

            except Exception as e:
                print(f"Error reading sheet {sheet_title}: {e}")

    except Exception as e:
        print(f"Error analyzing spreadsheet {file_name}: {e}")


def find_and_analyze_latest_outputs():
    """Find and analyze the most recent output files."""
    print("=== Analyzing Output Files Structure ===")

    # Get all files
    spreadsheets = analyze_monthly_invoicing_folder()

    # Filter for master timesheet files (generated outputs)
    master_files = [f for f in spreadsheets if "Timesheet_Master_" in f["name"]]

    print(f"\nFound {len(master_files)} master timesheet files:")
    for file in master_files:
        print(f"  - {file['name']} (Modified: {file['modifiedTime']})")

    # Analyze the most recent 2 files
    if master_files:
        print("\n=== Analyzing Latest Master Timesheet Files ===")
        for i, file in enumerate(master_files[:2]):  # Analyze top 2 most recent
            analyze_master_timesheet(file["id"], file["name"])
            if i < len(master_files) - 1:
                print("\n" + "=" * 60)

    return master_files


if __name__ == "__main__":
    load_dotenv()
    find_and_analyze_latest_outputs()
