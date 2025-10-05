"""Weekly hours calculator for generating capacity and utilization reports.

This module provides functionality to calculate weekly hours from aggregated
timesheet data, generate week-by-week matrices, and support flexible filtering.
"""

import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

import pandas as pd

from src.aggregators.timesheet_aggregator import AggregatedTimesheetData

logger = logging.getLogger(__name__)


@dataclass
class WeeklyHoursData:
    """Container for weekly hours data.

    This dataclass holds weekly aggregated hours for a specific freelancer
    and week.

    Attributes:
        freelancer_name: Name of the freelancer
        year: ISO year of the week
        week_number: ISO week number (1-53)
        billable_hours: Total billable hours for the week
        work_hours: Total work hours for the week
        entries_count: Number of timesheet entries in the week

    Example:
        >>> data = WeeklyHoursData(
        ...     freelancer_name="John Doe",
        ...     year=2023,
        ...     week_number=24,
        ...     billable_hours=Decimal("40.0"),
        ...     work_hours=Decimal("45.0"),
        ...     entries_count=5
        ... )
        >>> data.week_number
        24
    """

    freelancer_name: str
    year: int
    week_number: int
    billable_hours: Decimal
    work_hours: Decimal
    entries_count: int


class WeeklyHoursCalculator:
    """Calculates weekly hours and generates capacity reports.

    This class processes aggregated timesheet data to generate weekly
    summaries, create week-by-week matrices, and support filtering by
    project, freelancer, and date range.

    The calculator:
    1. Aggregates hours by freelancer and ISO week
    2. Handles year boundaries correctly (week 52/53 to week 1)
    3. Generates pandas DataFrame matrices for reporting
    4. Supports flexible filtering

    Example:
        >>> from src.aggregators.timesheet_aggregator import TimesheetAggregator
        >>> # ... setup aggregator and get data ...
        >>> calculator = WeeklyHoursCalculator()
        >>> weekly_data = calculator.calculate_weekly_hours(aggregated_data)
        >>> matrix = calculator.generate_weekly_matrix(weekly_data)
        >>> print(matrix.head())
    """

    def calculate_weekly_hours(
        self, data: AggregatedTimesheetData
    ) -> List[WeeklyHoursData]:
        """Calculate weekly hours from aggregated timesheet data.

        Groups timesheet entries by freelancer and ISO week, then aggregates
        billable hours, work hours, and entry counts for each group.

        Args:
            data: Aggregated timesheet data with entries and billing results

        Returns:
            List of WeeklyHoursData objects, one per freelancer-week combination

        Example:
            >>> weekly_hours = calculator.calculate_weekly_hours(data)
            >>> len(weekly_hours)
            52
        """
        logger.info(
            f"Calculating weekly hours for {len(data.entries)} timesheet entries"
        )

        if not data.entries:
            logger.info("No entries to process, returning empty list")
            return []

        # Group data by (freelancer, year, week)
        weekly_groups: Dict[
            Tuple[str, int, int], List[Tuple[int, Decimal, Decimal]]
        ] = defaultdict(list)

        for idx, entry in enumerate(data.entries):
            # Get ISO calendar year and week number
            iso_year, iso_week, _ = entry.date.isocalendar()

            # Get billing result for this entry
            billing_result = data.billing_results[idx]

            # Group by (freelancer, year, week)
            key = (entry.freelancer_name, iso_year, iso_week)
            weekly_groups[key].append(
                (1, billing_result.billable_hours, billing_result.work_hours)
            )

        # Aggregate each group
        result: List[WeeklyHoursData] = []

        for (freelancer_name, year, week_number), entries in weekly_groups.items():
            total_billable = sum(e[1] for e in entries)
            total_work = sum(e[2] for e in entries)
            count = sum(e[0] for e in entries)

            weekly_data = WeeklyHoursData(
                freelancer_name=freelancer_name,
                year=year,
                week_number=week_number,
                billable_hours=total_billable,
                work_hours=total_work,
                entries_count=count,
            )
            result.append(weekly_data)

        logger.info(f"Calculated {len(result)} weekly hour records")
        return result

    def generate_weekly_matrix(
        self, weekly_data: List[WeeklyHoursData]
    ) -> pd.DataFrame:
        """Generate week-by-week matrix from weekly hours data.

        Creates a pandas DataFrame with freelancers as rows and weeks as
        columns, showing billable hours for each cell.

        Args:
            weekly_data: List of weekly hours data

        Returns:
            DataFrame with freelancers as index, week labels as columns

        Example:
            >>> matrix = calculator.generate_weekly_matrix(weekly_data)
            >>> matrix.loc["John Doe", "2023-W24"]
            Decimal('40.0')
        """
        logger.info(f"Generating weekly matrix from {len(weekly_data)} records")

        if not weekly_data:
            logger.info("No weekly data, returning empty DataFrame")
            return pd.DataFrame()

        # Create dictionary for DataFrame construction
        # Structure: {freelancer: {week_label: hours}}
        matrix_data: Dict[str, Dict[str, Decimal]] = defaultdict(dict)

        for record in weekly_data:
            # Create week label in format "YYYY-W##"
            week_label = f"{record.year}-W{record.week_number:02d}"
            matrix_data[record.freelancer_name][week_label] = record.billable_hours

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(matrix_data, orient="index")

        # Fill NaN with 0 or keep as NaN (depends on requirements)
        # df = df.fillna(Decimal("0.0"))

        logger.info(
            f"Generated matrix with {len(df)} freelancers and {len(df.columns)} weeks"
        )

        return df

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
            >>> filtered = calculator.filter_by_project(data, "PROJ-001")
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
            >>> filtered = calculator.filter_by_date_range(
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

    def get_week_range(
        self,
        weekly_data: List[WeeklyHoursData],
        year: int,
        start_week: int,
        end_week: int,
    ) -> List[WeeklyHoursData]:
        """Get weekly data for specific week range.

        Filters weekly data to only include records within the specified
        week range for a given year.

        Args:
            weekly_data: List of weekly hours data
            year: Year to filter by
            start_week: Start week number (inclusive)
            end_week: End week number (inclusive)

        Returns:
            Filtered list of WeeklyHoursData

        Example:
            >>> week_range = calculator.get_week_range(
            ...     weekly_data,
            ...     year=2023,
            ...     start_week=20,
            ...     end_week=25
            ... )
            >>> len(week_range)
            6
        """
        logger.info(f"Getting week range for {year}: weeks {start_week} to {end_week}")

        filtered = [
            record
            for record in weekly_data
            if record.year == year and start_week <= record.week_number <= end_week
        ]

        logger.info(f"Found {len(filtered)} records in week range")
        return filtered
