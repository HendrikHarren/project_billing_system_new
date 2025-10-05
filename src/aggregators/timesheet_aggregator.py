"""Timesheet aggregator for combining multiple freelancer timesheets.

This module provides functionality to aggregate timesheet data from multiple
freelancers, merge with project terms, calculate trips and billing, and support
flexible filtering.
"""

import datetime as dt
import logging
from dataclasses import dataclass
from typing import List, Optional

from src.calculators.billing_calculator import BillingResult, calculate_billing_batch
from src.calculators.trip_calculator import calculate_trips
from src.models.timesheet import TimesheetEntry
from src.models.trip import Trip
from src.readers.project_terms_reader import ProjectTermsReader
from src.readers.timesheet_reader import TimesheetReader
from src.services.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)


@dataclass
class AggregatedTimesheetData:
    """Container for aggregated timesheet data.

    This dataclass holds the complete aggregated dataset including:
    - All timesheet entries from multiple freelancers
    - Calculated billing results for each entry
    - Identified trips (consecutive on-site days)

    Attributes:
        entries: List of all timesheet entries
        billing_results: List of billing calculations for each entry
        trips: List of identified trips from on-site work

    Example:
        >>> data = AggregatedTimesheetData(
        ...     entries=[entry1, entry2],
        ...     billing_results=[result1, result2],
        ...     trips=[trip1]
        ... )
        >>> len(data.entries)
        2
    """

    entries: List[TimesheetEntry]
    billing_results: List[BillingResult]
    trips: List[Trip]


class TimesheetAggregator:
    """Aggregates multiple freelancer timesheets into unified dataset.

    This class combines timesheet data from multiple freelancers stored in
    Google Drive, merges with project billing terms, calculates trips and
    billing amounts, and provides filtering capabilities.

    The aggregator:
    1. Reads all timesheet files from a Google Drive folder
    2. Parses and validates each timesheet
    3. Merges with project terms to get billing rates
    4. Calculates trips from consecutive on-site days
    5. Calculates billing for each entry
    6. Supports filtering by date range, project, or freelancer

    Attributes:
        timesheet_reader: Reader for individual timesheet files
        project_terms_reader: Reader for project billing terms
        drive_service: Google Drive service for folder operations

    Example:
        >>> from src.services.google_sheets_service import GoogleSheetsService
        >>> from src.services.google_drive_service import GoogleDriveService
        >>> from src.readers.timesheet_reader import TimesheetReader
        >>> from src.readers.project_terms_reader import ProjectTermsReader
        >>>
        >>> sheets_service = GoogleSheetsService()
        >>> drive_service = GoogleDriveService()
        >>> timesheet_reader = TimesheetReader(sheets_service)
        >>> project_terms_reader = ProjectTermsReader(sheets_service, "terms-id")
        >>>
        >>> aggregator = TimesheetAggregator(
        ...     timesheet_reader=timesheet_reader,
        ...     project_terms_reader=project_terms_reader,
        ...     drive_service=drive_service
        ... )
        >>>
        >>> data = aggregator.aggregate_timesheets("folder-id-123")
        >>> len(data.entries)
        150
    """

    def __init__(
        self,
        timesheet_reader: TimesheetReader,
        project_terms_reader: ProjectTermsReader,
        drive_service: GoogleDriveService,
    ):
        """Initialize the timesheet aggregator.

        Args:
            timesheet_reader: Reader for individual timesheet files
            project_terms_reader: Reader for project billing terms
            drive_service: Google Drive service for folder operations
        """
        self.timesheet_reader = timesheet_reader
        self.project_terms_reader = project_terms_reader
        self.drive_service = drive_service

    def aggregate_timesheets(
        self,
        folder_id: str,
        start_date: Optional[dt.date] = None,
        end_date: Optional[dt.date] = None,
        project_code: Optional[str] = None,
        freelancer_name: Optional[str] = None,
    ) -> AggregatedTimesheetData:
        """Aggregate all timesheets from a Google Drive folder with optional filtering.

        This method:
        1. Lists all timesheet files in the specified folder
        2. Reads and parses each timesheet
        3. Applies filters (defaults: current year + previous year for performance)
        4. Loads project billing terms
        5. Calculates billing for filtered entries only
        6. Identifies trips from consecutive on-site work
        7. Returns unified dataset

        Args:
            folder_id: Google Drive folder ID containing timesheet files
            start_date: Filter entries >= this date (default: Jan 1 of previous year)
            end_date: Filter entries <= this date (default: Dec 31 of current year)
            project_code: Filter by project code (optional, no default)
            freelancer_name: Filter by freelancer name (optional, no default)

        Returns:
            AggregatedTimesheetData with filtered entries, billing results, and trips

        Raises:
            KeyError: If billing terms not found for a freelancer-project combination
            Exception: If there are errors accessing Google Drive or reading files

        Note:
            By default, filters to current year + previous year to prevent pivot table
            performance issues. This is a safety measure to avoid processing too much
            data which would make pivot tables unusably slow.

        Example:
            >>> # Default: current year + previous year
            >>> data = aggregator.aggregate_timesheets("1abc...xyz")
            >>> # Filter by specific date range
            >>> data = aggregator.aggregate_timesheets(
            ...     "1abc...xyz",
            ...     start_date=dt.date(2023, 6, 1),
            ...     end_date=dt.date(2023, 6, 30)
            ... )
            >>> # Filter by multiple criteria
            >>> data = aggregator.aggregate_timesheets(
            ...     "1abc...xyz",
            ...     start_date=dt.date(2023, 6, 1),
            ...     project_code="PROJ-001",
            ...     freelancer_name="John Doe"
            ... )
        """
        logger.info(f"Starting timesheet aggregation from folder: {folder_id}")

        # Apply default date filter: current year + previous year
        # This prevents pivot table performance issues with too much data
        today = dt.date.today()
        current_year = today.year

        if start_date is None:
            start_date = dt.date(current_year - 1, 1, 1)  # Jan 1 of previous year
            logger.info(f"Using default start_date: {start_date}")

        if end_date is None:
            end_date = dt.date(current_year, 12, 31)  # Dec 31 of current year
            logger.info(f"Using default end_date: {end_date}")

        logger.info(f"Date filter: {start_date} to {end_date}")
        if project_code:
            logger.info(f"Project filter: {project_code}")
        if freelancer_name:
            logger.info(f"Freelancer filter: {freelancer_name}")

        # Step 1: List all timesheet files in folder
        try:
            files = self.drive_service.list_files_in_folder(folder_id)
            logger.info(f"Found {len(files)} timesheet files in folder")
        except Exception as e:
            logger.error(f"Failed to list files in folder {folder_id}: {e}")
            raise

        # Return empty data if no files found
        if not files:
            logger.info("No timesheet files found in folder")
            return AggregatedTimesheetData(entries=[], billing_results=[], trips=[])

        # Step 2: Read all timesheets
        all_entries: List[TimesheetEntry] = []

        for file_info in files:
            file_id = file_info["id"]
            file_name = file_info["name"]

            try:
                logger.debug(f"Reading timesheet: {file_name} (ID: {file_id})")
                entries = self.timesheet_reader.read_timesheet(file_id)
                all_entries.extend(entries)
                logger.info(f"Read {len(entries)} entries from {file_name}")
            except Exception as e:
                logger.warning(
                    f"Failed to read timesheet {file_name} (ID: {file_id}): {e}. "
                    f"Skipping this file."
                )
                continue

        logger.info(f"Successfully read {len(all_entries)} total timesheet entries")

        # Return empty data if no entries found
        if not all_entries:
            logger.info("No timesheet entries found")
            return AggregatedTimesheetData(entries=[], billing_results=[], trips=[])

        # Step 3: Apply filters to entries (before calculating billing)
        filtered_entries = all_entries

        # Apply date range filters (start_date and end_date always set by defaults)
        filtered_entries = [
            e for e in filtered_entries if start_date <= e.date <= end_date
        ]
        logger.info(
            f"Filtered by date range {start_date} to {end_date}: "
            f"{len(filtered_entries)} entries remaining"
        )

        # Apply project filter
        if project_code is not None:
            filtered_entries = [
                e for e in filtered_entries if e.project_code == project_code
            ]
            logger.info(
                f"Filtered by project_code '{project_code}': "
                f"{len(filtered_entries)} entries remaining"
            )

        # Apply freelancer filter
        if freelancer_name is not None:
            filtered_entries = [
                e for e in filtered_entries if e.freelancer_name == freelancer_name
            ]
            logger.info(
                f"Filtered by freelancer_name '{freelancer_name}': "
                f"{len(filtered_entries)} entries remaining"
            )

        # Return empty data if filtering resulted in no entries
        if not filtered_entries:
            logger.info("No entries match the specified filters")
            return AggregatedTimesheetData(entries=[], billing_results=[], trips=[])

        logger.info(
            f"After filtering: {len(filtered_entries)} entries "
            f"(reduced from {len(all_entries)})"
        )

        # Step 4: Load project billing terms
        try:
            terms_map = self.project_terms_reader.get_all_project_terms()
            logger.info(f"Loaded billing terms for {len(terms_map)} combinations")
        except Exception as e:
            logger.error(f"Failed to load project terms: {e}")
            raise

        # Step 5: Calculate billing for filtered entries only
        try:
            billing_results = calculate_billing_batch(filtered_entries, terms_map)
            logger.info(f"Calculated billing for {len(billing_results)} entries")
        except KeyError as e:
            logger.error(f"Missing billing terms: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to calculate billing: {e}")
            raise

        # Step 6: Calculate trips from consecutive on-site days (filtered entries only)
        try:
            trips = calculate_trips(filtered_entries)
            logger.info(f"Identified {len(trips)} trips from timesheet data")
        except Exception as e:
            logger.error(f"Failed to calculate trips: {e}")
            raise

        # Step 7: Return aggregated data
        result = AggregatedTimesheetData(
            entries=filtered_entries, billing_results=billing_results, trips=trips
        )

        logger.info(
            f"Aggregation complete: {len(result.entries)} entries, "
            f"{len(result.billing_results)} billing results, {len(result.trips)} trips"
        )

        return result

    def filter_by_date_range(
        self,
        data: AggregatedTimesheetData,
        start_date: dt.date,
        end_date: dt.date,
    ) -> AggregatedTimesheetData:
        """Filter aggregated data by date range.

        Creates a new AggregatedTimesheetData with only entries falling within
        the specified date range (inclusive). Billing results and trips are
        also filtered to match.

        Args:
            data: Original aggregated data
            start_date: Start date of range (inclusive)
            end_date: End date of range (inclusive)

        Returns:
            New AggregatedTimesheetData with filtered entries

        Example:
            >>> filtered = aggregator.filter_by_date_range(
            ...     data,
            ...     start_date=dt.date(2023, 6, 1),
            ...     end_date=dt.date(2023, 6, 30)
            ... )
            >>> len(filtered.entries)
            45
        """
        logger.info(f"Filtering data by date range: {start_date} to {end_date}")

        # Filter entries by date range
        filtered_entries = [
            entry for entry in data.entries if start_date <= entry.date <= end_date
        ]

        # Get indices of filtered entries to match billing results
        entry_indices = [
            i
            for i, entry in enumerate(data.entries)
            if start_date <= entry.date <= end_date
        ]

        # Filter billing results to match entries
        filtered_billing = [data.billing_results[i] for i in entry_indices]

        # Filter trips that fall within date range
        filtered_trips = [
            trip
            for trip in data.trips
            if trip.start_date <= end_date and trip.end_date >= start_date
        ]

        logger.info(
            f"Filtered to {len(filtered_entries)} entries, "
            f"{len(filtered_trips)} trips"
        )

        return AggregatedTimesheetData(
            entries=filtered_entries,
            billing_results=filtered_billing,
            trips=filtered_trips,
        )

    def filter_by_project(
        self, data: AggregatedTimesheetData, project_code: str
    ) -> AggregatedTimesheetData:
        """Filter aggregated data by project code.

        Creates a new AggregatedTimesheetData with only entries for the
        specified project. Billing results and trips are also filtered to match.

        Args:
            data: Original aggregated data
            project_code: Project code to filter by

        Returns:
            New AggregatedTimesheetData with filtered entries

        Example:
            >>> filtered = aggregator.filter_by_project(data, "PROJ-001")
            >>> all(e.project_code == "PROJ-001" for e in filtered.entries)
            True
        """
        logger.info(f"Filtering data by project: {project_code}")

        # Filter entries by project
        filtered_entries = [
            entry for entry in data.entries if entry.project_code == project_code
        ]

        # Get indices of filtered entries to match billing results
        entry_indices = [
            i
            for i, entry in enumerate(data.entries)
            if entry.project_code == project_code
        ]

        # Filter billing results to match entries
        filtered_billing = [data.billing_results[i] for i in entry_indices]

        # Filter trips by project
        filtered_trips = [
            trip for trip in data.trips if trip.project_code == project_code
        ]

        logger.info(
            f"Filtered to {len(filtered_entries)} entries, "
            f"{len(filtered_trips)} trips"
        )

        return AggregatedTimesheetData(
            entries=filtered_entries,
            billing_results=filtered_billing,
            trips=filtered_trips,
        )

    def filter_by_freelancer(
        self, data: AggregatedTimesheetData, freelancer_name: str
    ) -> AggregatedTimesheetData:
        """Filter aggregated data by freelancer name.

        Creates a new AggregatedTimesheetData with only entries for the
        specified freelancer. Billing results and trips are also filtered to match.

        Args:
            data: Original aggregated data
            freelancer_name: Freelancer name to filter by

        Returns:
            New AggregatedTimesheetData with filtered entries

        Example:
            >>> filtered = aggregator.filter_by_freelancer(data, "John Doe")
            >>> all(e.freelancer_name == "John Doe" for e in filtered.entries)
            True
        """
        logger.info(f"Filtering data by freelancer: {freelancer_name}")

        # Filter entries by freelancer
        filtered_entries = [
            entry for entry in data.entries if entry.freelancer_name == freelancer_name
        ]

        # Get indices of filtered entries to match billing results
        entry_indices = [
            i
            for i, entry in enumerate(data.entries)
            if entry.freelancer_name == freelancer_name
        ]

        # Filter billing results to match entries
        filtered_billing = [data.billing_results[i] for i in entry_indices]

        # Filter trips by freelancer
        filtered_trips = [
            trip for trip in data.trips if trip.freelancer_name == freelancer_name
        ]

        logger.info(
            f"Filtered to {len(filtered_entries)} entries, "
            f"{len(filtered_trips)} trips"
        )

        return AggregatedTimesheetData(
            entries=filtered_entries,
            billing_results=filtered_billing,
            trips=filtered_trips,
        )
