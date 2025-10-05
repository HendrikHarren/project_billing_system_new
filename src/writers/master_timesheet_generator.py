"""Master timesheet generator for creating formatted output DataFrames.

This module generates master timesheet and trips DataFrames from aggregated
timesheet data, with proper formatting for dates, times, and calculations.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
from src.calculators.billing_calculator import BillingResult
from src.models.timesheet import TimesheetEntry
from src.models.trip import Trip


@dataclass
class MasterTimesheetData:
    """Container for all master timesheet output data.

    Attributes:
        timesheet_master: Main timesheet DataFrame with 24 columns
        trips_master: Trips DataFrame with 7 columns
    """

    timesheet_master: pd.DataFrame
    trips_master: pd.DataFrame


class MasterTimesheetGenerator:
    """Generate master timesheet DataFrames from aggregated data.

    This class transforms AggregatedTimesheetData into formatted DataFrames
    ready for output to Google Sheets, with all calculations completed and
    proper formatting applied.

    Example:
        >>> generator = MasterTimesheetGenerator(aggregated_data)
        >>> result = generator.generate()
        >>> print(len(result.timesheet_master.columns))
        24
        >>> print(result.timesheet_master["Date"].iloc[0])
        '2023-06-15'
    """

    def __init__(self, aggregated_data: AggregatedTimesheetData):
        """Initialize with aggregated timesheet data.

        Args:
            aggregated_data: Aggregated data from TimesheetAggregator
        """
        self.aggregated_data = aggregated_data

    def generate(self) -> MasterTimesheetData:
        """Generate all master timesheet DataFrames.

        Returns:
            MasterTimesheetData with timesheet_master and trips_master DataFrames
        """
        timesheet_df = self._generate_timesheet_master()
        trips_df = self._generate_trips_master()
        return MasterTimesheetData(timesheet_master=timesheet_df, trips_master=trips_df)

    def _generate_timesheet_master(self) -> pd.DataFrame:
        """Generate 24-column timesheet master DataFrame.

        Returns:
            DataFrame with all timesheet entries, billing calculations,
            and trip information properly formatted.
        """
        if not self.aggregated_data.entries:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=self._get_timesheet_columns())

        # Build trip lookup dictionary
        trip_lookup = self._build_trip_lookup()

        # Build rows
        rows = []
        for i, entry in enumerate(self.aggregated_data.entries):
            billing = self.aggregated_data.billing_results[i]
            row = self._build_timesheet_row(entry, billing, trip_lookup)
            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows, columns=self._get_timesheet_columns())

        return df

    def _generate_trips_master(self) -> pd.DataFrame:
        """Generate trips master DataFrame (7 columns).

        Returns:
            DataFrame with trip information for trips with non-zero reimbursement.
        """
        if not self.aggregated_data.trips:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=self._get_trips_columns())

        rows = []
        for trip in self.aggregated_data.trips:
            # Only include trips with reimbursement > 0
            # For now, we'll include all trips; filtering will be done
            # when trip reimbursement data is available
            row = {
                "Name": trip.freelancer_name,
                "Project": trip.project_code,
                "Location": trip.location,
                "Trip Start Date": self._format_date(trip.start_date),
                "Trip Duration": trip.duration_days,
                "Trip Reimbursement": 0,  # Will be filled by TripAggregator
                "Month": trip.start_date.month,
            }
            rows.append(row)

        df = pd.DataFrame(rows, columns=self._get_trips_columns())

        return df

    def _build_trip_lookup(self) -> Dict[tuple, Trip]:
        """Build lookup dictionary for trips.

        Returns:
            Dictionary mapping (name, date, project, location) to Trip object
        """
        trip_lookup = {}

        for trip in self.aggregated_data.trips:
            # Create entries for each day in the trip
            current_date = trip.start_date
            while current_date <= trip.end_date:
                key = (
                    trip.freelancer_name,
                    current_date,
                    trip.project_code,
                    trip.location,
                )
                trip_lookup[key] = trip
                current_date += dt.timedelta(days=1)

        return trip_lookup

    def _build_timesheet_row(
        self,
        entry: TimesheetEntry,
        billing: BillingResult,
        trip_lookup: Dict[tuple, Trip],
    ) -> Dict:
        """Build a single row for the timesheet master DataFrame.

        Args:
            entry: Timesheet entry
            billing: Billing result for this entry
            trip_lookup: Dictionary for looking up trip information

        Returns:
            Dictionary with all 24 column values
        """
        # Look up trip information
        trip_key = (
            entry.freelancer_name,
            entry.date,
            entry.project_code,
            entry.location,
        )
        trip = trip_lookup.get(trip_key)

        # Determine location format (legacy uses "Off-site" and "On-site")
        location = "On-site" if entry.location == "onsite" else "Off-site"

        row = {
            "Name": entry.freelancer_name,
            "Date": self._format_date(entry.date),
            "Project": entry.project_code,
            "Location": location,
            "Start Time": self._format_time(entry.start_time),
            "End Time": self._format_time(entry.end_time),
            "Topics worked on": entry.notes or "",
            "Break": self._format_minutes_as_time(entry.break_minutes),
            "Travel time": self._format_minutes_as_time(entry.travel_time_minutes),
            "Trip Start Date": self._format_date(trip.start_date) if trip else "",
            "Trip Duration": trip.duration_days if trip else 0,
            "Rate": float(billing.hourly_rate),
            "Cost": float(billing.cost_per_hour),
            "Share of travel as work": 0.5,  # From legacy: 50% of travel time
            "surcharge for travel": 0.15,  # From legacy: 15% travel surcharge
            "Hours": float(billing.total_hours),
            "Hours billed": float(billing.revenue),
            "Hours cost": float(billing.cost),
            "Travel hours billed": float(billing.travel_surcharge_hours),
            "Travel surcharge billed": float(billing.travel_surcharge_revenue),
            "Travel surcharge cost": float(billing.travel_surcharge_cost),
            "Year": entry.date.year,
            "Month": entry.date.month,
            "Week": entry.date.isocalendar().week,
        }

        return row

    def _get_timesheet_columns(self) -> List[str]:
        """Get the 24 column names for timesheet master.

        Returns:
            List of column names in correct order
        """
        return [
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

    def _get_trips_columns(self) -> List[str]:
        """Get the 7 column names for trips master.

        Returns:
            List of column names in correct order
        """
        return [
            "Name",
            "Project",
            "Location",
            "Trip Start Date",
            "Trip Duration",
            "Trip Reimbursement",
            "Month",
        ]

    def _format_date(self, date_obj: dt.date) -> str:
        """Format date as YYYY-MM-DD string.

        Args:
            date_obj: Date to format

        Returns:
            Formatted date string
        """
        return date_obj.strftime("%Y-%m-%d")

    def _format_time(self, time_obj: dt.time) -> str:
        """Format time as HH:MM string.

        Args:
            time_obj: Time to format

        Returns:
            Formatted time string
        """
        return time_obj.strftime("%H:%M")

    def _format_minutes_as_time(self, minutes: int) -> str:
        """Format minutes as HH:MM string.

        Args:
            minutes: Number of minutes

        Returns:
            Formatted time string (e.g., "01:30")
        """
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
