"""Unit tests for TripAggregator."""

from datetime import date
from decimal import Decimal

import pytest

from src.aggregators.trip_aggregator import AggregatedTripData, TripAggregator
from src.models.trip import Trip


@pytest.fixture
def sample_trips():
    """Create sample trips for testing."""
    return [
        Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 2),  # 2 days
        ),
        Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Munich",
            start_date=date(2023, 6, 5),
            end_date=date(2023, 6, 9),  # 5 days
        ),
        Trip(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            location="Hamburg",
            start_date=date(2023, 6, 12),
            end_date=date(2023, 6, 12),  # 1 day
        ),
        Trip(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            location="Frankfurt",
            start_date=date(2023, 7, 3),
            end_date=date(2023, 7, 5),  # 3 days (different month)
        ),
    ]


@pytest.fixture
def trip_terms():
    """Create sample trip reimbursement terms."""
    return [
        {
            "min_days": 1,
            "max_days": 2,
            "reimbursement_type": "Per Diem",
            "amount_per_day": Decimal("50.00"),
        },
        {
            "min_days": 3,
            "max_days": 7,
            "reimbursement_type": "Per Diem",
            "amount_per_day": Decimal("45.00"),
        },
        {
            "min_days": 8,
            "max_days": 14,
            "reimbursement_type": "Per Diem",
            "amount_per_day": Decimal("40.00"),
        },
    ]


class TestTripAggregator:
    """Test TripAggregator class."""

    def test_aggregate_trips_empty_list(self, trip_terms):
        """Test aggregating empty trip list returns empty data."""
        aggregator = TripAggregator()
        result = aggregator.aggregate_trips([], trip_terms)

        assert isinstance(result, AggregatedTripData)
        assert result.trips == []
        assert result.reimbursements == []

    def test_aggregate_trips_no_terms(self, sample_trips):
        """Test aggregating trips with no terms returns empty reimbursements."""
        aggregator = TripAggregator()
        result = aggregator.aggregate_trips(sample_trips, [])

        assert len(result.trips) == 4
        assert len(result.reimbursements) == 0

    def test_aggregate_trips_calculates_reimbursements(self, sample_trips, trip_terms):
        """Test that reimbursements are calculated correctly for each trip."""
        aggregator = TripAggregator()
        result = aggregator.aggregate_trips(sample_trips, trip_terms)

        assert len(result.trips) == 4
        assert len(result.reimbursements) == 4

        # Check first trip (2 days, tier 1-2 days @ 50.00/day)
        assert result.reimbursements[0].trip == sample_trips[0]
        assert result.reimbursements[0].reimbursement_amount == Decimal("100.00")
        assert result.reimbursements[0].reimbursement_type == "Per Diem"

        # Check second trip (5 days, tier 3-7 days @ 45.00/day)
        assert result.reimbursements[1].trip == sample_trips[1]
        assert result.reimbursements[1].reimbursement_amount == Decimal("225.00")
        assert result.reimbursements[1].reimbursement_type == "Per Diem"

        # Check third trip (1 day, tier 1-2 days @ 50.00/day)
        assert result.reimbursements[2].trip == sample_trips[2]
        assert result.reimbursements[2].reimbursement_amount == Decimal("50.00")

        # Check fourth trip (3 days, tier 3-7 days @ 45.00/day)
        assert result.reimbursements[3].trip == sample_trips[3]
        assert result.reimbursements[3].reimbursement_amount == Decimal("135.00")

    def test_aggregate_trips_filters_zero_reimbursements(self):
        """Test that trips with zero reimbursements are excluded."""
        aggregator = TripAggregator()

        trips = [
            Trip(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                location="Berlin",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 2),
            ),
            Trip(
                freelancer_name="Jane Smith",
                project_code="PROJ-002",
                location="Munich",
                start_date=date(2023, 6, 5),
                end_date=date(2023, 6, 20),  # 16 days - no matching tier
            ),
        ]

        trip_terms = [
            {
                "min_days": 1,
                "max_days": 2,
                "reimbursement_type": "Per Diem",
                "amount_per_day": Decimal("50.00"),
            }
        ]

        result = aggregator.aggregate_trips(trips, trip_terms)

        # Only first trip has reimbursement
        assert len(result.trips) == 1
        assert len(result.reimbursements) == 1
        assert result.trips[0] == trips[0]
        assert result.reimbursements[0].reimbursement_amount == Decimal("100.00")

    def test_filter_by_month(self, sample_trips, trip_terms):
        """Test filtering aggregated data by month."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        # Filter to June 2023
        result = aggregator.filter_by_month(data, year=2023, month=6)

        assert len(result.trips) == 3  # First 3 trips are in June
        assert len(result.reimbursements) == 3
        assert all(
            trip.start_date.month == 6 or trip.end_date.month == 6
            for trip in result.trips
        )

    def test_filter_by_month_different_month(self, sample_trips, trip_terms):
        """Test filtering by different month."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        # Filter to July 2023
        result = aggregator.filter_by_month(data, year=2023, month=7)

        assert len(result.trips) == 1  # Only last trip is in July
        assert len(result.reimbursements) == 1
        assert result.trips[0].start_date.month == 7

    def test_filter_by_freelancer(self, sample_trips, trip_terms):
        """Test filtering aggregated data by freelancer."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        result = aggregator.filter_by_freelancer(data, "John Doe")

        assert len(result.trips) == 2  # John has 2 trips
        assert len(result.reimbursements) == 2
        assert all(trip.freelancer_name == "John Doe" for trip in result.trips)

    def test_filter_by_project(self, sample_trips, trip_terms):
        """Test filtering aggregated data by project."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        result = aggregator.filter_by_project(data, "PROJ-002")

        assert len(result.trips) == 2  # Jane's 2 trips on PROJ-002
        assert len(result.reimbursements) == 2
        assert all(trip.project_code == "PROJ-002" for trip in result.trips)

    def test_get_summary_statistics(self, sample_trips, trip_terms):
        """Test generating summary statistics."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        stats = aggregator.get_summary_statistics(data)

        assert stats["total_trips"] == 4
        assert stats["total_reimbursement"] == Decimal("510.00")
        assert stats["average_duration"] == Decimal("2.75")  # (2+5+1+3)/4
        assert stats["average_reimbursement"] == Decimal("127.50")  # 510/4
        assert stats["min_duration"] == 1
        assert stats["max_duration"] == 5

    def test_get_summary_statistics_empty_data(self):
        """Test summary statistics with empty data."""
        aggregator = TripAggregator()
        data = AggregatedTripData(trips=[], reimbursements=[])

        stats = aggregator.get_summary_statistics(data)

        assert stats["total_trips"] == 0
        assert stats["total_reimbursement"] == Decimal("0")
        assert stats["average_duration"] == Decimal("0")
        assert stats["average_reimbursement"] == Decimal("0")
        assert stats["min_duration"] == 0
        assert stats["max_duration"] == 0

    def test_trip_terms_matching_edge_cases(self):
        """Test edge cases in trip term matching."""
        aggregator = TripAggregator()

        trips = [
            Trip(
                freelancer_name="John",
                project_code="PROJ",
                location="Berlin",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 7),  # Exactly 7 days
            )
        ]

        trip_terms = [
            {
                "min_days": 3,
                "max_days": 7,
                "reimbursement_type": "Per Diem",
                "amount_per_day": Decimal("45.00"),
            }
        ]

        result = aggregator.aggregate_trips(trips, trip_terms)

        # Should match the 3-7 day tier
        assert len(result.reimbursements) == 1
        assert result.reimbursements[0].reimbursement_amount == Decimal("315.00")

    def test_multiple_freelancers_same_project(self, trip_terms):
        """Test handling multiple freelancers on same project."""
        aggregator = TripAggregator()

        trips = [
            Trip(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                location="Berlin",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 2),
            ),
            Trip(
                freelancer_name="Jane Smith",
                project_code="PROJ-001",
                location="Berlin",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 2),
            ),
        ]

        result = aggregator.aggregate_trips(trips, trip_terms)

        assert len(result.trips) == 2
        assert len(result.reimbursements) == 2
        # Both should have same reimbursement amount
        assert result.reimbursements[0].reimbursement_amount == Decimal("100.00")
        assert result.reimbursements[1].reimbursement_amount == Decimal("100.00")

    def test_filter_preserves_data_integrity(self, sample_trips, trip_terms):
        """Test filtering maintains trip-reimbursement correspondence."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        # Filter by freelancer
        filtered = aggregator.filter_by_freelancer(data, "Jane Smith")

        # Check that trips and reimbursements match
        for i, trip in enumerate(filtered.trips):
            assert filtered.reimbursements[i].trip == trip
            assert filtered.reimbursements[i].trip.freelancer_name == "Jane Smith"

    def test_group_by_month_returns_dict(self, sample_trips, trip_terms):
        """Test grouping trips by month returns dictionary."""
        aggregator = TripAggregator()
        data = aggregator.aggregate_trips(sample_trips, trip_terms)

        grouped = aggregator.group_by_month(data)

        assert isinstance(grouped, dict)
        assert (2023, 6) in grouped
        assert (2023, 7) in grouped

        # June should have 3 trips
        june_data = grouped[(2023, 6)]
        assert len(june_data.trips) == 3

        # July should have 1 trip
        july_data = grouped[(2023, 7)]
        assert len(july_data.trips) == 1
