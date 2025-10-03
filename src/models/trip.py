"""Trip data models for billing system.

This module defines the Trip and TripReimbursement models which represent
business trips and their associated reimbursements.
"""
import datetime as dt
from decimal import Decimal
from typing import Union

from pydantic import Field, computed_field, field_validator, model_validator

from src.models.base import BaseDataModel


class Trip(BaseDataModel):
    """Represents a business trip.

    This model captures information about consecutive on-site days for
    a freelancer at a specific location and project.

    Attributes:
        freelancer_name: Name of the freelancer
        project_code: Project identifier
        location: Trip location/city
        start_date: First day of the trip
        end_date: Last day of the trip
        duration_days: Computed field - number of days (inclusive)

    Example:
        >>> trip = Trip(
        ...     freelancer_name="John Doe",
        ...     project_code="PROJ-001",
        ...     location="Berlin",
        ...     start_date=dt.date(2023, 6, 1),
        ...     end_date=dt.date(2023, 6, 5)
        ... )
        >>> trip.duration_days
        5
    """

    freelancer_name: str = Field(..., min_length=1, description="Freelancer's name")
    project_code: str = Field(..., min_length=1, description="Project identifier")
    location: str = Field(..., min_length=1, description="Trip location/city")
    start_date: dt.date = Field(..., description="First day of trip")
    end_date: dt.date = Field(..., description="Last day of trip")

    @field_validator("freelancer_name", "project_code", "location")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate that string fields are not empty or whitespace only.

        Args:
            v: The value to validate
            info: Field validation info

        Returns:
            The validated value

        Raises:
            ValueError: If the value is empty or whitespace only
        """
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def validate_dates(self) -> "Trip":
        """Validate that end_date is not before start_date.

        Returns:
            The validated model instance

        Raises:
            ValueError: If end_date is before start_date
        """
        if self.end_date < self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) cannot be before "
                f"start_date ({self.start_date})"
            )
        return self

    @computed_field  # type: ignore[misc]
    @property
    def duration_days(self) -> int:
        """Calculate trip duration in days (inclusive).

        Returns:
            Number of days from start_date to end_date (inclusive)

        Example:
            >>> # Trip from June 1 to June 5 is 5 days
            >>> trip = Trip(..., start_date=date(2023, 6, 1), end_date=date(2023, 6, 5))
            >>> trip.duration_days
            5
        """
        return (self.end_date - self.start_date).days + 1


class TripReimbursement(BaseDataModel):
    """Represents a trip reimbursement.

    This model captures financial reimbursement information for a business trip.

    Attributes:
        trip: The associated Trip object
        reimbursement_amount: Reimbursement amount in currency units
        reimbursement_type: Type of reimbursement (e.g., "Per Diem", "Flat Rate")

    Example:
        >>> trip = Trip(...)
        >>> reimbursement = TripReimbursement(
        ...     trip=trip,
        ...     reimbursement_amount=Decimal("500.00"),
        ...     reimbursement_type="Per Diem"
        ... )
        >>> reimbursement.reimbursement_amount
        Decimal('500.00')
    """

    trip: Trip = Field(..., description="Associated trip")
    reimbursement_amount: Decimal = Field(..., ge=0, description="Reimbursement amount")
    reimbursement_type: str = Field(
        ..., min_length=1, description="Type of reimbursement"
    )

    @field_validator("reimbursement_type")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate that reimbursement_type is not empty or whitespace only.

        Args:
            v: The value to validate
            info: Field validation info

        Returns:
            The validated value

        Raises:
            ValueError: If the value is empty or whitespace only
        """
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        return v.strip()

    @field_validator("reimbursement_amount", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: Union[str, int, float, Decimal]) -> Decimal:
        """Convert numeric values to Decimal for precision.

        Args:
            v: The value to convert

        Returns:
            The value as a Decimal

        Raises:
            ValueError: If the value cannot be converted to Decimal
        """
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert {v} to Decimal: {e}")
