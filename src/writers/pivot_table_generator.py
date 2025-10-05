"""Pivot table generator for creating summary DataFrames.

This module generates pre-computed pivot tables as pandas DataFrames,
which is superior to native Google Sheets pivot tables because:
- Fully testable without Google API
- Faster rendering in Google Sheets
- Deterministic output
- Version controllable
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class PivotTableData:
    """Container for pivot table DataFrames.

    Attributes:
        pivot_master: Financial summary DataFrame
        weekly_reporting: Weekly hours matrix DataFrame
    """

    pivot_master: pd.DataFrame
    weekly_reporting: pd.DataFrame


class PivotTableGenerator:
    """Generate pivot tables as pre-computed pandas DataFrames.

    This class creates summary tables from the master timesheet data:
    - Pivot_master: Financial summary grouped by name, date, location
    - Weekly_reporting: Weekly hours matrix (freelancers × weeks)

    Example:
        >>> generator = PivotTableGenerator(timesheet_df)
        >>> pivot_data = generator.generate()
        >>> print(len(pivot_data.pivot_master))
        50
    """

    def __init__(self, timesheet_df: pd.DataFrame):
        """Initialize with timesheet master DataFrame.

        Args:
            timesheet_df: Master timesheet DataFrame with 24 columns
        """
        self.timesheet_df = timesheet_df

    def generate(
        self,
        project_filter: Optional[str] = None,
        year_filter: Optional[int] = None,
        month_filter: Optional[int] = None,
    ) -> PivotTableData:
        """Generate all pivot tables with optional filters.

        Args:
            project_filter: Filter by project code (e.g., "P&C_NEWRETAIL")
            year_filter: Filter by year (e.g., 2023)
            month_filter: Filter by month (e.g., 6 for June)

        Returns:
            PivotTableData with both pivot tables
        """
        pivot_master = self._generate_pivot_master(
            project_filter, year_filter, month_filter
        )
        weekly_reporting = self._generate_weekly_reporting(project_filter, year_filter)
        return PivotTableData(
            pivot_master=pivot_master, weekly_reporting=weekly_reporting
        )

    def _generate_pivot_master(
        self,
        project: Optional[str],
        year: Optional[int],
        month: Optional[int],
    ) -> pd.DataFrame:
        """Generate financial summary pivot table.

        Creates a grouped summary with rows for each unique combination of:
        Name, Date, Location, Start Time, End Time, Topics worked on,
        Break, Travel time

        Columns show aggregated financial metrics.

        Args:
            project: Optional project filter
            year: Optional year filter
            month: Optional month filter

        Returns:
            DataFrame with financial summary
        """
        df = self.timesheet_df.copy()

        # Apply filters
        if project:
            df = df[df["Project"] == project]
        if year:
            df = df[df["Year"] == year]
        if month:
            df = df[df["Month"] == month]

        if len(df) == 0:
            # Return empty DataFrame with correct structure
            return pd.DataFrame(
                columns=[
                    "Name",
                    "Date",
                    "Location",
                    "Start Time",
                    "End Time",
                    "Topics worked on",
                    "Break",
                    "Travel time",
                    "Hours",
                    "Rate",
                    "Hours billed",
                    "Hours cost",
                    "Travel hours",
                    "Travel billed",
                    "Travel cost",
                    "Total billed",
                    "Agency Profit",
                ]
            )

        # Group by row dimensions
        group_cols = [
            "Name",
            "Date",
            "Location",
            "Start Time",
            "End Time",
            "Topics worked on",
            "Break",
            "Travel time",
        ]

        # Aggregate
        # Convert string columns to numeric for aggregation
        df_agg = df.copy()
        numeric_cols = [
            "Hours",
            "Rate",
            "Hours billed",
            "Hours cost",
            "Travel hours billed",
            "Travel surcharge billed",
            "Travel surcharge cost",
        ]

        for col in numeric_cols:
            if col in df_agg.columns:
                df_agg[col] = pd.to_numeric(df_agg[col], errors="coerce").fillna(0)

        grouped = df_agg.groupby(group_cols, as_index=False).agg(
            {
                "Hours": "sum",
                "Rate": "mean",
                "Hours billed": "sum",
                "Hours cost": "sum",
                "Travel hours billed": "sum",
                "Travel surcharge billed": "sum",
                "Travel surcharge cost": "sum",
            }
        )

        # Rename columns to match legacy output
        grouped = grouped.rename(
            columns={
                "Travel hours billed": "Travel hours",
                "Travel surcharge billed": "Travel billed",
                "Travel surcharge cost": "Travel cost",
            }
        )

        # Calculate formula columns
        grouped["Total billed"] = grouped["Hours billed"] + grouped["Travel billed"]
        grouped["Agency Profit"] = (
            grouped["Hours billed"]
            - grouped["Hours cost"]
            + grouped["Travel billed"]
            - grouped["Travel cost"]
        )

        # Reorder columns
        final_cols = [
            "Name",
            "Date",
            "Location",
            "Start Time",
            "End Time",
            "Topics worked on",
            "Break",
            "Travel time",
            "Hours",
            "Rate",
            "Hours billed",
            "Hours cost",
            "Travel hours",
            "Travel billed",
            "Travel cost",
            "Total billed",
            "Agency Profit",
        ]

        return grouped[final_cols]

    def _generate_weekly_reporting(
        self, project: Optional[str], year: Optional[int]
    ) -> pd.DataFrame:
        """Generate weekly hours matrix (freelancers × weeks).

        Creates a pivot table with:
        - Rows: Freelancer names
        - Columns: Week numbers (1-52)
        - Values: Sum of hours

        Args:
            project: Optional project filter
            year: Optional year filter

        Returns:
            DataFrame with weekly hours matrix
        """
        df = self.timesheet_df.copy()

        # Apply filters
        if project:
            df = df[df["Project"] == project]
        if year:
            df = df[df["Year"] == year]

        if len(df) == 0:
            # Return empty DataFrame with structure
            return pd.DataFrame(columns=["Name"] + [str(i) for i in range(1, 53)])

        # Convert Hours to numeric
        df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce").fillna(0)
        df["Week"] = pd.to_numeric(df["Week"], errors="coerce").fillna(1).astype(int)

        # Create pivot table
        pivot = df.pivot_table(
            index="Name", columns="Week", values="Hours", aggfunc="sum", fill_value=0
        )

        # Ensure we have all weeks 1-52
        all_weeks = range(1, 53)
        for week in all_weeks:
            if week not in pivot.columns:
                pivot[week] = 0

        # Sort columns
        pivot = pivot[sorted(pivot.columns)]

        # Reset index to make Name a column
        pivot = pivot.reset_index()

        # Rename columns to strings
        pivot.columns = ["Name"] + [str(col) for col in pivot.columns[1:]]

        return pivot
