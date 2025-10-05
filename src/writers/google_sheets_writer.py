"""Google Sheets writer for master timesheet output.

This module writes master timesheet data to Google Sheets with proper
formatting and structure (4 sheets).
"""

import logging
from datetime import datetime
from typing import Tuple

import pandas as pd

from src.writers.master_timesheet_generator import MasterTimesheetData
from src.writers.pivot_table_generator import PivotTableData

logger = logging.getLogger(__name__)


class GoogleSheetsWriter:
    """Write master timesheet data to Google Sheets with formatting.

    Creates a Google Sheets file with 4 sheets:
    1. Timesheet_master - All timesheet entries (24 columns)
    2. Trips_master - Trip reimbursements (7 columns)
    3. Pivot_master - Financial summary
    4. Weekly_reporting - Weekly hours matrix

    Example:
        >>> writer = GoogleSheetsWriter(sheets_service, drive_service)
        >>> file_id, url = writer.write_master_timesheet(
        ...     master_data, pivot_data, "folder-id"
        ... )
        >>> print(url)
        https://docs.google.com/spreadsheets/d/...
    """

    def __init__(self, sheets_service, drive_service):
        """Initialize with Google API services.

        Args:
            sheets_service: Google Sheets API service
            drive_service: Google Drive API service
        """
        self.sheets_service = sheets_service
        self.drive_service = drive_service

    def write_master_timesheet(
        self,
        master_data: MasterTimesheetData,
        pivot_data: PivotTableData,
        output_folder_id: str,
        filename_prefix: str = "Timesheet_Master",
    ) -> Tuple[str, str]:
        """Write complete master timesheet to Google Sheets.

        Args:
            master_data: Timesheet and trips DataFrames
            pivot_data: Pivot table DataFrames
            output_folder_id: Google Drive folder ID for output
            filename_prefix: Prefix for filename (default: "Timesheet_Master")

        Returns:
            Tuple of (file_id, file_url)
        """
        # Create spreadsheet
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        title = f"{filename_prefix}_{timestamp}"

        logger.info(f"Creating master timesheet spreadsheet: {title}")
        file_id = self._create_spreadsheet(title)

        # Write all sheets
        logger.info("Writing Timesheet_master sheet...")
        self._write_sheet(file_id, "Timesheet_master", master_data.timesheet_master)

        logger.info("Writing Trips_master sheet...")
        self._write_sheet(file_id, "Trips_master", master_data.trips_master)

        logger.info("Writing Pivot_master sheet...")
        self._write_sheet(file_id, "Pivot_master", pivot_data.pivot_master)

        logger.info("Writing Weekly_reporting sheet...")
        self._write_sheet(file_id, "Weekly_reporting", pivot_data.weekly_reporting)

        # Apply basic formatting
        logger.info("Applying formatting...")
        self._apply_basic_formatting(file_id)

        # Move to output folder
        logger.info(f"Moving to folder {output_folder_id}...")
        self._move_to_folder(file_id, output_folder_id)

        # Generate URL
        url = f"https://docs.google.com/spreadsheets/d/{file_id}"

        logger.info(f"Successfully created master timesheet: {url}")
        return file_id, url

    def _create_spreadsheet(self, title: str) -> str:
        """Create new spreadsheet with 4 sheets.

        Args:
            title: Spreadsheet title

        Returns:
            Spreadsheet file ID
        """
        spreadsheet = {
            "properties": {"title": title},
            "sheets": [
                {"properties": {"sheetId": 0, "title": "Timesheet_master"}},
                {"properties": {"sheetId": 1, "title": "Trips_master"}},
                {"properties": {"sheetId": 2, "title": "Pivot_master"}},
                {"properties": {"sheetId": 3, "title": "Weekly_reporting"}},
            ],
        }

        result = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
        return result.get("spreadsheetId")

    def _write_sheet(self, file_id: str, sheet_name: str, df: pd.DataFrame):
        """Write DataFrame to sheet.

        Args:
            file_id: Spreadsheet file ID
            sheet_name: Sheet name
            df: DataFrame to write
        """
        # Convert DataFrame to list of lists
        values = [df.columns.tolist()] + df.values.tolist()

        # Write to sheet
        range_name = f"{sheet_name}!A1"
        body = {"values": values}

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=file_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

    def _apply_basic_formatting(self, file_id: str):
        """Apply basic formatting to all sheets.

        Applies:
        - Header row formatting (bold, gray background, centered)
        - Freeze header row
        - Auto-resize columns

        Args:
            file_id: Spreadsheet file ID
        """
        requests = []

        # Format all 4 sheets
        for sheet_id in range(4):
            # Header formatting
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.9,
                                    "green": 0.9,
                                    "blue": 0.9,
                                },
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 10,
                                },
                            }
                        },
                        "fields": (
                            "userEnteredFormat(backgroundColor,"
                            "horizontalAlignment,textFormat)"
                        ),
                    }
                }
            )

            # Freeze header row
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                }
            )

            # Auto-resize columns
            requests.append(
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                        }
                    }
                }
            )

        # Apply all formatting
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=file_id, body={"requests": requests}
        ).execute()

    def _move_to_folder(self, file_id: str, folder_id: str):
        """Move file to specified folder.

        Args:
            file_id: File ID to move
            folder_id: Target folder ID
        """
        # Get current parents
        file = (
            self.drive_service.files().get(fileId=file_id, fields="parents").execute()
        )
        previous_parents = ",".join(file.get("parents", []))

        # Move to new folder
        self.drive_service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()
