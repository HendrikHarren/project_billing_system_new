"""Unit tests for Trip and TripReimbursement models."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestTripModel:
    """Test Trip model creation and validation."""

    def test_create_valid_trip(self):
        """Test creating a trip with valid data."""
        from src.models.trip import Trip

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        assert trip.freelancer_name == "John Doe"
        assert trip.project_code == "PROJ-001"
        assert trip.location == "Berlin"
        assert trip.start_date == date(2023, 6, 1)
        assert trip.end_date == date(2023, 6, 5)
        assert trip.duration_days == 5

    def test_single_day_trip(self):
        """Test that single-day trip has duration of 1."""
        from src.models.trip import Trip

        trip = Trip(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            location="Munich",
            start_date=date(2023, 6, 15),
            end_date=date(2023, 6, 15),
        )

        assert trip.duration_days == 1

    def test_multi_week_trip(self):
        """Test trip spanning multiple weeks."""
        from src.models.trip import Trip

        trip = Trip(
            freelancer_name="Alice Brown",
            project_code="PROJ-003",
            location="Hamburg",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 30),
        )

        assert trip.duration_days == 30

    def test_end_date_before_start_date_raises_error(self):
        """Test that end date before start date raises validation error."""
        from src.models.trip import Trip

        with pytest.raises(ValidationError) as exc_info:
            Trip(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                location="Berlin",
                start_date=date(2023, 6, 10),
                end_date=date(2023, 6, 5),  # Before start date
            )

        error_msg = str(exc_info.value).lower()
        assert "end_date" in error_msg or "start_date" in error_msg

    def test_empty_freelancer_name_raises_error(self):
        """Test that empty freelancer name raises validation error."""
        from src.models.trip import Trip

        with pytest.raises(ValidationError) as exc_info:
            Trip(
                freelancer_name="",
                project_code="PROJ-001",
                location="Berlin",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 5),
            )

        assert "freelancer_name" in str(exc_info.value).lower()

    def test_empty_location_raises_error(self):
        """Test that empty location raises validation error."""
        from src.models.trip import Trip

        with pytest.raises(ValidationError) as exc_info:
            Trip(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                location="",
                start_date=date(2023, 6, 1),
                end_date=date(2023, 6, 5),
            )

        assert "location" in str(exc_info.value).lower()

    def test_trip_serialization(self):
        """Test that trip can be serialized to dict."""
        from src.models.trip import Trip

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        data = trip.model_dump()
        assert data["freelancer_name"] == "John Doe"
        assert data["location"] == "Berlin"
        assert data["duration_days"] == 5

    def test_date_string_parsing(self):
        """Test that date strings can be parsed automatically."""
        from src.models.trip import Trip

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date="2023-06-01",
            end_date="2023-06-05",
        )

        assert trip.start_date == date(2023, 6, 1)
        assert trip.end_date == date(2023, 6, 5)


class TestTripReimbursementModel:
    """Test TripReimbursement model creation and validation."""

    def test_create_valid_trip_reimbursement(self):
        """Test creating a trip reimbursement with valid data."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        reimbursement = TripReimbursement(
            trip=trip,
            reimbursement_amount=Decimal("500.00"),
            reimbursement_type="Per Diem",
        )

        assert reimbursement.trip == trip
        assert reimbursement.reimbursement_amount == Decimal("500.00")
        assert reimbursement.reimbursement_type == "Per Diem"

    def test_zero_reimbursement_allowed(self):
        """Test that zero reimbursement is valid."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="Remote Worker",
            project_code="PROJ-002",
            location="Home Office",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 1),
        )

        reimbursement = TripReimbursement(
            trip=trip, reimbursement_amount=Decimal("0"), reimbursement_type="None"
        )

        assert reimbursement.reimbursement_amount == Decimal("0")

    def test_negative_reimbursement_raises_error(self):
        """Test that negative reimbursement raises validation error."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        with pytest.raises(ValidationError) as exc_info:
            TripReimbursement(
                trip=trip,
                reimbursement_amount=Decimal("-100.00"),
                reimbursement_type="Per Diem",
            )

        assert "reimbursement_amount" in str(exc_info.value).lower()

    def test_empty_reimbursement_type_raises_error(self):
        """Test that empty reimbursement type raises validation error."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        with pytest.raises(ValidationError) as exc_info:
            TripReimbursement(
                trip=trip, reimbursement_amount=Decimal("500.00"), reimbursement_type=""
            )

        assert "reimbursement_type" in str(exc_info.value).lower()

    def test_float_reimbursement_converted_to_decimal(self):
        """Test that float reimbursement is converted to Decimal."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            location="Munich",
            start_date=date(2023, 6, 10),
            end_date=date(2023, 6, 15),
        )

        reimbursement = TripReimbursement(
            trip=trip,
            reimbursement_amount=350.50,  # Float
            reimbursement_type="Flat Rate",
        )

        assert isinstance(reimbursement.reimbursement_amount, Decimal)
        assert reimbursement.reimbursement_amount == Decimal("350.50")

    def test_string_reimbursement_converted_to_decimal(self):
        """Test that string reimbursement is converted to Decimal."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="Alice Brown",
            project_code="PROJ-003",
            location="Hamburg",
            start_date=date(2023, 6, 20),
            end_date=date(2023, 6, 25),
        )

        reimbursement = TripReimbursement(
            trip=trip,
            reimbursement_amount="425.75",  # String
            reimbursement_type="Daily Rate",
        )

        assert reimbursement.reimbursement_amount == Decimal("425.75")

    def test_trip_reimbursement_serialization(self):
        """Test that trip reimbursement can be serialized to dict."""
        from src.models.trip import Trip, TripReimbursement

        trip = Trip(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            location="Berlin",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 6, 5),
        )

        reimbursement = TripReimbursement(
            trip=trip,
            reimbursement_amount=Decimal("500.00"),
            reimbursement_type="Per Diem",
        )

        data = reimbursement.model_dump()
        assert data["reimbursement_amount"] == Decimal("500.00")
        assert data["reimbursement_type"] == "Per Diem"
        assert data["trip"]["freelancer_name"] == "John Doe"
