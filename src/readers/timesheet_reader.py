"""Timesheet reader for extracting data from Google Sheets.

This module provides functionality to read and parse freelancer timesheet data
from Google Sheets, converting it into validated TimesheetEntry objects.
"""

import datetime as dt
import logging
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import ValidationError

from src.models.timesheet import TimesheetEntry
from src.services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)


class TimesheetReader:
    """Reader for extracting timesheet data from Google Sheets.

    This class handles reading timesheet data from Google Sheets, parsing
    various date/time formats, handling missing data, and creating validated
    TimesheetEntry objects.

    The expected sheet format:
    - Row 1: Headers
    - Row 2: Example row (skipped)
    - Row 3+: Actual data

    Columns:
    - Date: Work date (YYYY-MM-DD, DD.MM.YYYY, or MM/DD/YYYY)
    - Project: Project code
    - Location: 'On-site' or 'Off-site'
    - Start Time: Work start time (HH:MM)
    - End Time: Work end time (HH:MM)
    - Topics worked on: Optional notes
    - Break: Break duration (HH:MM)
    - Travel time: Travel duration (HH:MM)

    Attributes:
        sheets_service: Google Sheets service for data access

    Example:
        >>> from src.services.google_sheets_service import GoogleSheetsService
        >>> sheets_service = GoogleSheetsService()
        >>> reader = TimesheetReader(sheets_service)
        >>> entries = reader.read_timesheet("spreadsheet-id-123")
        >>> len(entries)
        42
    """

    def __init__(self, sheets_service: GoogleSheetsService):
        """Initialize the timesheet reader.

        Args:
            sheets_service: Google Sheets service instance for data access
        """
        self.sheets_service = sheets_service

    def read_timesheet(
        self,
        spreadsheet_id: str,
        sheet_name: str = "Timesheet",
        start_row: int = 3,
    ) -> List[TimesheetEntry]:
        """Read and parse timesheet data from Google Sheets.

        Args:
            spreadsheet_id: The ID of the Google Sheets spreadsheet
            sheet_name: Name of the sheet to read (default: "Timesheet")
            start_row: Row number to start reading (default: 3, skip headers)

        Returns:
            List of validated TimesheetEntry objects

        Raises:
            Exception: If there are errors accessing the spreadsheet

        Example:
            >>> entries = reader.read_timesheet("1abc...xyz")
            >>> entries[0].freelancer_name
            'John Doe'
        """
        try:
            # Get spreadsheet metadata to extract freelancer name
            metadata = self.sheets_service.get_sheet_metadata(spreadsheet_id)
            freelancer_name = self._extract_freelancer_name(metadata)

            logger.info(
                f"Reading timesheet for {freelancer_name} "
                f"from spreadsheet {spreadsheet_id}"
            )

            # Read data starting from row 3 (skip header and example)
            range_name = f"{sheet_name}!A{start_row}:I"
            df = self.sheets_service.read_sheet(spreadsheet_id, range_name)

            if df.empty:
                logger.info(f"No data found in {spreadsheet_id}")
                return []

            # Parse each row into TimesheetEntry objects
            entries = []
            for _, row in df.iterrows():
                entry = self._parse_row(row.to_dict(), freelancer_name)
                if entry:
                    entries.append(entry)

            logger.info(
                f"Successfully parsed {len(entries)} timesheet entries "
                f"for {freelancer_name}"
            )
            return entries

        except Exception as e:
            logger.error(f"Failed to read timesheet from {spreadsheet_id}: {e}")
            raise

    def _extract_freelancer_name(self, metadata: Dict[str, Any]) -> str:
        """Extract freelancer name from spreadsheet title.

        The title is expected to be in the format: "Firstname_Lastname_Timesheet"
        or "Firstname_Middlename_Lastname_Timesheet".

        Args:
            metadata: Spreadsheet metadata containing title

        Returns:
            Freelancer name with spaces instead of underscores

        Example:
            >>> metadata = {"properties": {"title": "John_Doe_Timesheet"}}
            >>> reader._extract_freelancer_name(metadata)
            'John Doe'
        """
        title = metadata.get("properties", {}).get("title", "")

        # Remove "_Timesheet" suffix if present
        if title.endswith("_Timesheet"):
            title = title[: -len("_Timesheet")]

        # Replace underscores with spaces
        name = title.replace("_", " ")

        logger.debug(f"Extracted freelancer name: {name}")
        return name

    def _parse_row(
        self, row: Dict[str, Any], freelancer_name: str
    ) -> Optional[TimesheetEntry]:
        """Parse a single timesheet row into a TimesheetEntry.

        Args:
            row: Dictionary containing row data
            freelancer_name: Name of the freelancer

        Returns:
            TimesheetEntry object if row is valid, None if row should be skipped

        Note:
            Empty rows, rows with missing dates, or rows with invalid data
            are skipped with appropriate logging.
        """
        try:
            # Get and clean field values
            date_str = str(row.get("Date", "")).strip()
            project_code = str(row.get("Project", "")).strip()
            location_str = str(row.get("Location", "")).strip()
            start_time_str = str(row.get("Start Time", "")).strip()
            end_time_str = str(row.get("End Time", "")).strip()
            notes_str = str(row.get("Topics worked on", "")).strip()
            break_str = str(row.get("Break", "")).strip()
            travel_str = str(row.get("Travel time", "")).strip()

            # Skip empty rows (missing date is considered empty)
            if not date_str or date_str == "nan":
                return None

            # Parse date
            try:
                parsed_date = self._parse_date(date_str)
            except ValueError as e:
                logger.warning(f"Skipping row with invalid date '{date_str}': {e}")
                return None

            # Parse times
            try:
                start_time = self._parse_time(start_time_str)
                end_time = self._parse_time(end_time_str)
            except ValueError as e:
                logger.warning(f"Skipping row for {parsed_date} with invalid time: {e}")
                return None

            # Determine if overnight shift
            is_overnight = end_time < start_time

            # Parse location
            try:
                location = self._normalize_location(location_str)
            except ValueError as e:
                logger.warning(
                    f"Skipping row for {parsed_date} "
                    f"with invalid location '{location_str}': {e}"
                )
                return None

            # Parse break and travel time
            break_minutes = self._time_to_minutes(break_str) if break_str else 0
            travel_minutes = self._time_to_minutes(travel_str) if travel_str else 0

            # Handle notes
            notes = notes_str if notes_str and notes_str != "nan" else None

            # Create and validate TimesheetEntry
            entry = TimesheetEntry(
                freelancer_name=freelancer_name,
                date=parsed_date,
                project_code=project_code,
                start_time=start_time,
                end_time=end_time,
                break_minutes=break_minutes,
                travel_time_minutes=travel_minutes,
                location=location,
                notes=notes,
                is_overnight=is_overnight,
            )

            return entry

        except ValidationError as e:
            logger.warning(f"Validation error for row: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing row: {e}")
            return None

    def _parse_date(self, date_str: str) -> dt.date:
        """Parse date string in multiple formats.

        Supports:
        - ISO format: YYYY-MM-DD
        - European format: DD.MM.YYYY
        - US format: MM/DD/YYYY

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date object

        Raises:
            ValueError: If date format is not recognized or invalid
        """
        date_str = date_str.strip()

        # Try different date formats
        formats = [
            "%Y-%m-%d",  # ISO format: 2023-06-15
            "%d.%m.%Y",  # European format: 15.06.2023
            "%m/%d/%Y",  # US format: 06/15/2023
        ]

        for fmt in formats:
            try:
                return dt.datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Invalid date format: {date_str}")

    def _parse_time(self, time_str: str) -> dt.time:
        """Parse time string in HH:MM or H:MM format.

        Args:
            time_str: Time string to parse (e.g., "09:30" or "9:30")

        Returns:
            Parsed time object

        Raises:
            ValueError: If time format is invalid
        """
        time_str = time_str.strip()

        # Handle both HH:MM and H:MM formats
        match = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        hours = int(match.group(1))
        minutes = int(match.group(2))

        # Validate ranges
        if hours < 0 or hours > 23:
            raise ValueError(f"Invalid time format: hours must be 0-23, got {hours}")
        if minutes < 0 or minutes > 59:
            raise ValueError(
                f"Invalid time format: minutes must be 0-59, got {minutes}"
            )

        return dt.time(hours, minutes)

    def _normalize_location(self, location: str) -> Literal["remote", "onsite"]:
        """Normalize location string to 'remote' or 'onsite'.

        Handles:
        - 'On-site' -> 'onsite'
        - 'Off-site' -> 'remote'
        - Location prefixes (e.g., 'Munich On-site' -> 'onsite')
        - Case insensitive matching

        Args:
            location: Location string from spreadsheet

        Returns:
            Normalized location ('remote' or 'onsite')

        Raises:
            ValueError: If location is not recognized
        """
        location_lower = location.lower()

        if "on-site" in location_lower or "onsite" in location_lower:
            return "onsite"
        elif (
            "off-site" in location_lower
            or "offsite" in location_lower
            or "remote" in location_lower
        ):
            return "remote"
        else:
            raise ValueError(f"Invalid location: {location}")

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to total minutes.

        Args:
            time_str: Time string in HH:MM format

        Returns:
            Total minutes as integer

        Example:
            >>> reader._time_to_minutes("01:30")
            90
        """
        time_str = time_str.strip()

        if not time_str or time_str == "00:00":
            return 0

        # Parse the time and convert to minutes
        time_obj = self._parse_time(time_str)
        return time_obj.hour * 60 + time_obj.minute
