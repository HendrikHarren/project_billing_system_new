"""Google Sheets writer for master timesheet output.

This module writes master timesheet data to Google Sheets with proper
formatting and structure (4 sheets: 2 static + 2 pivot tables).
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd

from src.writers.master_timesheet_generator import MasterTimesheetData

logger = logging.getLogger(__name__)


class GoogleSheetsWriter:
    """Write master timesheet data to Google Sheets with formatting.

    Creates a Google Sheets file with 4 sheets:
    1. Timesheet_master - All timesheet entries (24 columns) [static data]
    2. Trips_master - Trip reimbursements (7 columns) [static data]
    3. Pivot_master - Financial summary [native Google Sheets pivot table]
    4. Weekly_reporting - Weekly hours matrix [native Google Sheets pivot table]

    Example:
        >>> writer = GoogleSheetsWriter(sheets_service, drive_service)
        >>> file_id, url = writer.write_master_timesheet(
        ...     master_data, "folder-id",
        ...     project_filter="P&C_NEWRETAIL", year_filter=2023, month_filter=6
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
        output_folder_id: str,
        filename_prefix: str = "Timesheet_Master",
        project_filter: Optional[str] = None,
        year_filter: Optional[int] = None,
        month_filter: Optional[int] = None,
    ) -> Tuple[str, str]:
        """Write complete master timesheet to Google Sheets.

        Args:
            master_data: Timesheet and trips DataFrames
            output_folder_id: Google Drive folder ID for output
            filename_prefix: Prefix for filename (default: "Timesheet_Master")
            project_filter: Project code filter for pivot tables
            year_filter: Year filter for pivot tables
            month_filter: Month filter for pivot tables (only for Pivot_master)

        Returns:
            Tuple of (file_id, file_url)
        """
        # Create spreadsheet
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        title = f"{filename_prefix}_{timestamp}"

        logger.info(f"Creating master timesheet spreadsheet: {title}")
        file_id = self._create_spreadsheet(title)

        # Write static sheets
        logger.info("Writing Timesheet_master sheet...")
        self._write_sheet(file_id, "Timesheet_master", master_data.timesheet_master)

        logger.info("Writing Trips_master sheet...")
        self._write_sheet(file_id, "Trips_master", master_data.trips_master)

        # Apply basic formatting to static sheets
        logger.info("Applying formatting to static sheets...")
        self._apply_static_sheets_formatting(file_id)

        # Create pivot tables
        logger.info("Creating Pivot_master pivot table...")
        self._create_pivot_master(file_id, project_filter, year_filter, month_filter)

        logger.info("Creating Weekly_reporting pivot table...")
        self._create_weekly_reporting(file_id, project_filter, year_filter)

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

    def _apply_static_sheets_formatting(self, file_id: str):
        """Apply formatting to static sheets (Timesheet_master, Trips_master).

        Applies:
        - Header row formatting (bold, gray background, centered)
        - Freeze header row
        - Auto-resize columns
        - Custom width for "Topics worked on" column (Timesheet_master only)

        Args:
            file_id: Spreadsheet file ID
        """
        requests = []

        # Format sheets 0 and 1 (Timesheet_master, Trips_master)
        for sheet_id in range(2):
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

        # Set custom width for "Topics worked on" column (G) in Timesheet_master
        # Column G = index 6 (0-based)
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": 0,  # Timesheet_master
                        "dimension": "COLUMNS",
                        "startIndex": 6,
                        "endIndex": 7,
                    },
                    "properties": {"pixelSize": 200},
                    "fields": "pixelSize",
                }
            }
        )

        # Apply all formatting
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=file_id, body={"requests": requests}
        ).execute()

    def _create_pivot_master(
        self,
        file_id: str,
        project_filter: Optional[str],
        year_filter: Optional[int],
        month_filter: Optional[int],
    ):
        """Create native Google Sheets pivot table for Pivot_master.

        Args:
            file_id: Spreadsheet file ID
            project_filter: Project code filter
            year_filter: Year filter
            month_filter: Month filter
        """
        source_sheet_id = 0  # Timesheet_master
        target_sheet_id = 2  # Pivot_master

        # Build criteria filters
        criteria = {}
        if project_filter:
            criteria["2"] = {"visibleValues": [project_filter]}  # Column C (Project)
        if year_filter:
            criteria["21"] = {"visibleValues": [str(year_filter)]}  # Column V (Year)
        if month_filter:
            criteria["22"] = {"visibleValues": [str(month_filter)]}  # Column W (Month)

        requests = [
            {
                "updateCells": {
                    "rows": {
                        "values": [
                            {
                                "pivotTable": {
                                    "source": {
                                        "sheetId": source_sheet_id,
                                        "startRowIndex": 0,
                                        "startColumnIndex": 0,
                                    },
                                    "rows": [
                                        {
                                            "sourceColumnOffset": 0,
                                            "showTotals": True,
                                            "sortOrder": "ASCENDING",
                                        },  # Name
                                        {
                                            "sourceColumnOffset": 1,
                                            "showTotals": True,
                                            "sortOrder": "ASCENDING",
                                        },  # Date
                                        {
                                            "sourceColumnOffset": 3,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # Location
                                        {
                                            "sourceColumnOffset": 4,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # Start Time
                                        {
                                            "sourceColumnOffset": 5,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # End Time
                                        {
                                            "sourceColumnOffset": 6,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # Topics
                                        {
                                            "sourceColumnOffset": 7,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # Break
                                        {
                                            "sourceColumnOffset": 8,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        },  # Travel time
                                    ],
                                    "columns": [],
                                    "criteria": criteria,
                                    "values": [
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Hours",
                                            "sourceColumnOffset": 15,
                                        },
                                        {
                                            "summarizeFunction": "AVERAGE",
                                            "name": "Rate",
                                            "sourceColumnOffset": 11,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Hours billed",
                                            "sourceColumnOffset": 16,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Hours cost",
                                            "sourceColumnOffset": 17,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Travel hours",
                                            "sourceColumnOffset": 18,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Travel surcharge billed",
                                            "sourceColumnOffset": 19,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Travel surcharge cost",
                                            "sourceColumnOffset": 20,
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Total billed",
                                            "formula": (
                                                "='Hours billed'"
                                                "+'Travel surcharge billed'"
                                            ),
                                        },
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Agency Profit",
                                            "formula": (
                                                "='Hours billed'-'Hours cost'"
                                                "+'Travel surcharge billed'"
                                                "-'Travel surcharge cost'"
                                            ),
                                        },
                                    ],
                                    "valueLayout": "HORIZONTAL",
                                }
                            }
                        ]
                    },
                    "start": {
                        "sheetId": target_sheet_id,
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "fields": "pivotTable",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": target_sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": target_sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                    }
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": target_sheet_id,
                        "gridProperties": {"frozenColumnCount": 1},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
        ]

        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=file_id, body={"requests": requests}
        ).execute()

    def _create_weekly_reporting(
        self,
        file_id: str,
        project_filter: Optional[str],
        year_filter: Optional[int],
    ):
        """Create native Google Sheets pivot table for Weekly_reporting.

        Args:
            file_id: Spreadsheet file ID
            project_filter: Project code filter
            year_filter: Year filter
        """
        source_sheet_id = 0  # Timesheet_master
        target_sheet_id = 3  # Weekly_reporting

        # Build criteria filters
        criteria = {}
        if project_filter:
            criteria["2"] = {"visibleValues": [project_filter]}  # Column C (Project)
        if year_filter:
            criteria["21"] = {"visibleValues": [str(year_filter)]}  # Column V (Year)

        requests = [
            {
                "updateCells": {
                    "rows": {
                        "values": [
                            {
                                "pivotTable": {
                                    "source": {
                                        "sheetId": source_sheet_id,
                                        "startRowIndex": 0,
                                        "startColumnIndex": 0,
                                    },
                                    "rows": [
                                        {
                                            "sourceColumnOffset": 0,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        }  # Name
                                    ],
                                    "columns": [
                                        {
                                            "sourceColumnOffset": 23,
                                            "showTotals": False,
                                            "sortOrder": "ASCENDING",
                                        }  # Week
                                    ],
                                    "criteria": criteria,
                                    "values": [
                                        {
                                            "summarizeFunction": "SUM",
                                            "name": "Hours",
                                            "sourceColumnOffset": 15,
                                        }
                                    ],
                                    "valueLayout": "HORIZONTAL",
                                }
                            }
                        ]
                    },
                    "start": {
                        "sheetId": target_sheet_id,
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "fields": "pivotTable",
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": target_sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": target_sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                    }
                }
            },
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": target_sheet_id,
                        "gridProperties": {"frozenColumnCount": 1},
                    },
                    "fields": "gridProperties.frozenColumnCount",
                }
            },
        ]

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
