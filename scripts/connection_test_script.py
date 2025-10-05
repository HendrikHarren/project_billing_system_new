"""
Simple script to test Google API connection and list timesheet files.
This is our MVP test to verify access to input and output files.
"""
import os

from dotenv import load_dotenv

from src.google_auth import get_drive_service, get_sheets_service


def test_drive_connection():
    """Test Google Drive connection and list files in timesheet folder."""
    print("Testing Google Drive connection...")

    try:
        drive_service = get_drive_service()
        timesheet_folder_id = os.getenv("TIMESHEET_FOLDER_ID")

        print(f"Listing files in timesheet folder: {timesheet_folder_id}")

        # List files in the timesheet folder
        response = (
            drive_service.files()
            .list(
                q=f"'{timesheet_folder_id}' in parents",
                fields="files(id, name, modifiedTime)",
            )
            .execute()
        )

        files = response.get("files", [])
        print(f"Found {len(files)} files:")

        for file in files:
            print(
                f"  - {file['name']} (ID: {file['id']}, "
                f"Modified: {file['modifiedTime']})"
            )

        return files

    except Exception as e:
        print(f"Error connecting to Google Drive: {e}")
        return []


def test_sheets_connection(file_id: str):
    """Test Google Sheets connection by reading a specific timesheet."""
    print(f"\nTesting Google Sheets connection with file ID: {file_id}")

    try:
        sheets_service = get_sheets_service()

        # Get spreadsheet properties
        sheet_properties = (
            sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
        )
        sheet_title = sheet_properties["properties"]["title"]
        print(f"Spreadsheet title: {sheet_title}")

        # Read timesheet data
        range_name = "Timesheet!A:H"
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=file_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        print(f"Found {len(values)} rows of data")

        if values:
            print("Headers:", values[0])
            if len(values) > 1:
                print("Sample data row:", values[1])

        return values

    except Exception as e:
        print(f"Error reading spreadsheet: {e}")
        return []


def test_project_terms():
    """Test reading the project terms spreadsheet."""
    print("\nTesting project terms spreadsheet...")

    try:
        sheets_service = get_sheets_service()
        project_terms_file_id = os.getenv("PROJECT_TERMS_FILE_ID")

        # Read main terms
        main_result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=project_terms_file_id, range="Main terms!A:G")
            .execute()
        )

        main_terms = main_result.get("values", [])
        print(f"Main terms: {len(main_terms)} rows")
        if main_terms:
            print("Main terms headers:", main_terms[0])

        # Read trip terms
        trip_result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=project_terms_file_id, range="Trip terms!A:C")
            .execute()
        )

        trip_terms = trip_result.get("values", [])
        print(f"Trip terms: {len(trip_terms)} rows")
        if trip_terms:
            print("Trip terms headers:", trip_terms[0])

        return main_terms, trip_terms

    except Exception as e:
        print(f"Error reading project terms: {e}")
        return [], []


if __name__ == "__main__":
    load_dotenv()

    print("=== Testing Google API Access ===")

    # Test Drive connection
    files = test_drive_connection()

    # Test Sheets connection with first file found
    if files:
        test_sheets_connection(files[0]["id"])

    # Test project terms
    test_project_terms()

    print("\n=== Test completed ===")
