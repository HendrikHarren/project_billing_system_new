"""Project data models for billing system.

This module defines the Project and ProjectTerms models which represent
project information and freelancer-specific billing terms.
"""
from decimal import Decimal
from typing import Union

from pydantic import Field, field_validator, model_validator

from src.models.base import BaseDataModel


class Project(BaseDataModel):
    """Represents a project.

    This model captures basic project information including code, name, and client.

    Attributes:
        code: Unique project identifier (e.g., "PROJ-001")
        name: Project name
        client: Client name

    Example:
        >>> project = Project(
        ...     code="PROJ-001",
        ...     name="Website Redesign",
        ...     client="Acme Corp"
        ... )
        >>> project.code
        'PROJ-001'
    """

    code: str = Field(..., min_length=1, description="Unique project identifier")
    name: str = Field(..., min_length=1, description="Project name")
    client: str = Field(..., min_length=1, description="Client name")

    @field_validator("code", "name", "client")
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


class ProjectTerms(BaseDataModel):
    """Represents billing terms for a specific freelancer-project combination.

    This model captures all financial and billing information for a freelancer
    working on a specific project.

    Attributes:
        freelancer_name: Name of the freelancer
        project_code: Project identifier
        hourly_rate: Hourly billing rate in currency units
        travel_surcharge_percentage: Additional charge for on-site work (0-100)
        travel_time_percentage: Percentage of travel time to bill (0-100)
        cost_per_hour: Cost per hour (must be less than hourly_rate for profit)

    Example:
        >>> terms = ProjectTerms(
        ...     freelancer_name="John Doe",
        ...     project_code="PROJ-001",
        ...     hourly_rate=Decimal("85.00"),
        ...     travel_surcharge_percentage=Decimal("15.0"),
        ...     travel_time_percentage=Decimal("50.0"),
        ...     cost_per_hour=Decimal("60.00")
        ... )
        >>> terms.hourly_rate
        Decimal('85.00')
    """

    freelancer_name: str = Field(..., min_length=1, description="Freelancer's name")
    project_code: str = Field(..., min_length=1, description="Project identifier")
    hourly_rate: Decimal = Field(..., gt=0, description="Hourly billing rate")
    travel_surcharge_percentage: Decimal = Field(
        ..., ge=0, le=100, description="Travel surcharge percentage (0-100)"
    )
    travel_time_percentage: Decimal = Field(
        ..., ge=0, le=100, description="Travel time billing percentage (0-100)"
    )
    cost_per_hour: Decimal = Field(..., ge=0, description="Cost per hour")

    @field_validator("freelancer_name", "project_code")
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

    @field_validator(
        "hourly_rate",
        "travel_surcharge_percentage",
        "travel_time_percentage",
        "cost_per_hour",
        mode="before",
    )
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

    @model_validator(mode="after")
    def validate_profit_margin(self) -> "ProjectTerms":
        """Validate that cost is less than rate (ensuring profit).

        Returns:
            The validated model instance

        Raises:
            ValueError: If cost exceeds or equals hourly rate
        """
        if self.cost_per_hour >= self.hourly_rate:
            raise ValueError(
                f"cost_per_hour ({self.cost_per_hour}) must be less than "
                f"hourly_rate ({self.hourly_rate}) to ensure profit margin"
            )
        return self
