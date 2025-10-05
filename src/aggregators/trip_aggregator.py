"""Trip aggregator for organizing and calculating trip reimbursements.

This module provides functionality to aggregate trip data, calculate reimbursements
based on duration tiers, filter by various criteria, and generate summary statistics.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.models.trip import Trip, TripReimbursement

logger = logging.getLogger(__name__)


@dataclass
class AggregatedTripData:
    """Container for aggregated trip data with reimbursements.

    This dataclass holds the aggregated trip dataset including:
    - All trips with non-zero reimbursements
    - Calculated reimbursement amounts for each trip

    Attributes:
        trips: List of trips with reimbursements
        reimbursements: List of reimbursement calculations for each trip

    Example:
        >>> data = AggregatedTripData(
        ...     trips=[trip1, trip2],
        ...     reimbursements=[reimb1, reimb2]
        ... )
        >>> len(data.trips)
        2
    """

    trips: List[Trip]
    reimbursements: List[TripReimbursement]


class TripAggregator:
    """Aggregates trip data and calculates reimbursements.

    This class processes trip data to:
    1. Calculate reimbursements based on trip duration and terms
    2. Filter trips with non-zero reimbursements
    3. Support filtering by month, freelancer, and project
    4. Generate summary statistics

    The aggregator uses trip terms (duration tiers with per-day rates) to
    calculate reimbursement amounts. Only trips with matching terms and
    non-zero reimbursements are included in the results.

    Example:
        >>> aggregator = TripAggregator()
        >>> trip_terms = [
        ...     {"min_days": 1, "max_days": 2, "reimbursement_type": "Per Diem",
        ...      "amount_per_day": Decimal("50.00")}
        ... ]
        >>> data = aggregator.aggregate_trips(trips, trip_terms)
        >>> len(data.trips)
        5
    """

    def aggregate_trips(
        self, trips: List[Trip], trip_terms: List[Dict[str, Any]]
    ) -> AggregatedTripData:
        """Aggregate trips and calculate reimbursements.

        Processes each trip to:
        - Find matching reimbursement tier based on duration
        - Calculate reimbursement amount
        - Filter to only trips with non-zero reimbursements

        Args:
            trips: List of trips to process
            trip_terms: List of reimbursement term dictionaries with keys:
                - min_days: Minimum duration for this tier
                - max_days: Maximum duration for this tier
                - reimbursement_type: Type of reimbursement
                - amount_per_day: Daily reimbursement rate

        Returns:
            AggregatedTripData with trips and calculated reimbursements

        Example:
            >>> trips = [trip1, trip2]
            >>> terms = [{"min_days": 1, "max_days": 7, ...}]
            >>> data = aggregator.aggregate_trips(trips, terms)
            >>> len(data.trips)
            2
        """
        logger.info(f"Aggregating {len(trips)} trips with {len(trip_terms)} term tiers")

        if not trips:
            logger.info("No trips to aggregate")
            return AggregatedTripData(trips=[], reimbursements=[])

        if not trip_terms:
            logger.info(
                "No trip terms provided - returning trips without reimbursements"
            )
            return AggregatedTripData(trips=trips, reimbursements=[])

        filtered_trips: List[Trip] = []
        reimbursements: List[TripReimbursement] = []

        for trip in trips:
            # Find matching term tier for this trip's duration
            matching_term = self._find_matching_term(trip.duration_days, trip_terms)

            if matching_term:
                # Calculate reimbursement
                amount = matching_term["amount_per_day"] * trip.duration_days

                if amount > 0:
                    # Create reimbursement object
                    reimbursement = TripReimbursement(
                        trip=trip,
                        reimbursement_amount=amount,
                        reimbursement_type=matching_term["reimbursement_type"],
                    )

                    filtered_trips.append(trip)
                    reimbursements.append(reimbursement)
                    logger.debug(
                        f"Trip {trip.freelancer_name} {trip.location} "
                        f"({trip.duration_days} days): {amount}"
                    )

        logger.info(
            f"Aggregated {len(filtered_trips)} trips with non-zero reimbursements"
        )

        return AggregatedTripData(trips=filtered_trips, reimbursements=reimbursements)

    def filter_by_month(
        self, data: AggregatedTripData, year: int, month: int
    ) -> AggregatedTripData:
        """Filter aggregated data by month.

        Includes trips that start or end in the specified month.

        Args:
            data: Original aggregated data
            year: Year to filter by
            month: Month to filter by (1-12)

        Returns:
            New AggregatedTripData with filtered trips

        Example:
            >>> filtered = aggregator.filter_by_month(data, year=2023, month=6)
            >>> all(t.start_date.month == 6 or t.end_date.month == 6
            ...     for t in filtered.trips)
            True
        """
        logger.info(f"Filtering trips by month: {year}-{month:02d}")

        filtered_trips: List[Trip] = []
        filtered_reimbursements: List[TripReimbursement] = []

        for i, trip in enumerate(data.trips):
            # Include if trip starts or ends in target month
            if (
                trip.start_date.year == year
                and trip.start_date.month == month
                or trip.end_date.year == year
                and trip.end_date.month == month
            ):
                filtered_trips.append(trip)
                filtered_reimbursements.append(data.reimbursements[i])

        logger.info(f"Filtered to {len(filtered_trips)} trips")

        return AggregatedTripData(
            trips=filtered_trips, reimbursements=filtered_reimbursements
        )

    def filter_by_freelancer(
        self, data: AggregatedTripData, freelancer_name: str
    ) -> AggregatedTripData:
        """Filter aggregated data by freelancer name.

        Args:
            data: Original aggregated data
            freelancer_name: Freelancer name to filter by

        Returns:
            New AggregatedTripData with filtered trips

        Example:
            >>> filtered = aggregator.filter_by_freelancer(data, "John Doe")
            >>> all(t.freelancer_name == "John Doe" for t in filtered.trips)
            True
        """
        logger.info(f"Filtering trips by freelancer: {freelancer_name}")

        filtered_trips: List[Trip] = []
        filtered_reimbursements: List[TripReimbursement] = []

        for i, trip in enumerate(data.trips):
            if trip.freelancer_name == freelancer_name:
                filtered_trips.append(trip)
                filtered_reimbursements.append(data.reimbursements[i])

        logger.info(f"Filtered to {len(filtered_trips)} trips")

        return AggregatedTripData(
            trips=filtered_trips, reimbursements=filtered_reimbursements
        )

    def filter_by_project(
        self, data: AggregatedTripData, project_code: str
    ) -> AggregatedTripData:
        """Filter aggregated data by project code.

        Args:
            data: Original aggregated data
            project_code: Project code to filter by

        Returns:
            New AggregatedTripData with filtered trips

        Example:
            >>> filtered = aggregator.filter_by_project(data, "PROJ-001")
            >>> all(t.project_code == "PROJ-001" for t in filtered.trips)
            True
        """
        logger.info(f"Filtering trips by project: {project_code}")

        filtered_trips: List[Trip] = []
        filtered_reimbursements: List[TripReimbursement] = []

        for i, trip in enumerate(data.trips):
            if trip.project_code == project_code:
                filtered_trips.append(trip)
                filtered_reimbursements.append(data.reimbursements[i])

        logger.info(f"Filtered to {len(filtered_trips)} trips")

        return AggregatedTripData(
            trips=filtered_trips, reimbursements=filtered_reimbursements
        )

    def group_by_month(
        self, data: AggregatedTripData
    ) -> Dict[Tuple[int, int], AggregatedTripData]:
        """Group trips by month.

        Creates a dictionary mapping (year, month) tuples to aggregated data
        for trips in that month.

        Args:
            data: Original aggregated data

        Returns:
            Dictionary mapping (year, month) to AggregatedTripData

        Example:
            >>> grouped = aggregator.group_by_month(data)
            >>> (2023, 6) in grouped
            True
            >>> len(grouped[(2023, 6)].trips)
            5
        """
        logger.info("Grouping trips by month")

        grouped: Dict[Tuple[int, int], AggregatedTripData] = {}

        for i, trip in enumerate(data.trips):
            # Use start_date to determine month
            key = (trip.start_date.year, trip.start_date.month)

            if key not in grouped:
                grouped[key] = AggregatedTripData(trips=[], reimbursements=[])

            grouped[key].trips.append(trip)
            grouped[key].reimbursements.append(data.reimbursements[i])

        logger.info(f"Grouped into {len(grouped)} months")

        return grouped

    def get_summary_statistics(self, data: AggregatedTripData) -> Dict[str, Any]:
        """Generate summary statistics for aggregated trip data.

        Calculates:
        - Total number of trips
        - Total reimbursement amount
        - Average trip duration
        - Average reimbursement per trip
        - Min/max trip duration

        Args:
            data: Aggregated trip data

        Returns:
            Dictionary with summary statistics

        Example:
            >>> stats = aggregator.get_summary_statistics(data)
            >>> stats["total_trips"]
            10
            >>> stats["total_reimbursement"]
            Decimal('5000.00')
        """
        logger.info("Calculating summary statistics")

        if not data.trips:
            return {
                "total_trips": 0,
                "total_reimbursement": Decimal("0"),
                "average_duration": Decimal("0"),
                "average_reimbursement": Decimal("0"),
                "min_duration": 0,
                "max_duration": 0,
            }

        total_trips = len(data.trips)
        total_reimbursement = sum(r.reimbursement_amount for r in data.reimbursements)
        durations = [trip.duration_days for trip in data.trips]
        total_duration = sum(durations)

        stats = {
            "total_trips": total_trips,
            "total_reimbursement": total_reimbursement,
            "average_duration": Decimal(str(total_duration / total_trips)),
            "average_reimbursement": total_reimbursement / total_trips,
            "min_duration": min(durations),
            "max_duration": max(durations),
        }

        logger.info(
            f"Statistics: {total_trips} trips, "
            f"{total_reimbursement} total reimbursement"
        )

        return stats

    def _find_matching_term(
        self, duration_days: int, trip_terms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find matching trip term tier for a given duration.

        Args:
            duration_days: Trip duration in days
            trip_terms: List of trip term dictionaries

        Returns:
            Matching term dictionary or None if no match found

        Example:
            >>> term = aggregator._find_matching_term(5, trip_terms)
            >>> term["amount_per_day"]
            Decimal('45.00')
        """
        for term in trip_terms:
            if term["min_days"] <= duration_days <= term["max_days"]:
                return term

        logger.debug(f"No matching term found for duration {duration_days} days")
        return None
