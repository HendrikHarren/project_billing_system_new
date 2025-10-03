"""Timesheet data model for billing system.

This module defines the TimesheetEntry model which represents a single
timesheet entry for a freelancer on a specific date and project.
"""

import datetime as dt
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator

from src.models.base import BaseDataModel


class TimesheetEntry(BaseDataModel):
    """Represents a single timesheet entry.

    This model captures all information about a freelancer's work on a
    specific date, including hours worked, breaks, travel time, and location.

    Attributes:
        freelancer_name: Name of the freelancer
        date: Date of the work
        project_code: Project identifier (e.g., "PROJ-001")
        start_time: Work start time
        end_time: Work end time
        break_minutes: Break duration in minutes
        travel_time_minutes: Travel time in minutes
        location: Work location ('remote' or 'onsite')
        notes: Optional notes about the work
        is_overnight: Flag indicating if shift spans midnight

    Example:
        >>> entry = TimesheetEntry(
        ...     freelancer_name="John Doe",
        ...     date=dt.date(2023, 6, 15),
        ...     project_code="PROJ-001",
        ...     start_time=dt.time(9, 0),
        ...     end_time=dt.time(17, 0),
        ...     break_minutes=30,
        ...     travel_time_minutes=0,
        ...     location="remote"
        ... )
        >>> entry.freelancer_name
        'John Doe'
    """

    freelancer_name: str = Field(..., min_length=1, description="Freelancer's name")
    date: dt.date = Field(..., description="Date of work")
    project_code: str = Field(..., min_length=1, description="Project identifier")
    start_time: dt.time = Field(..., description="Work start time")
    end_time: dt.time = Field(..., description="Work end time")
    break_minutes: int = Field(..., ge=0, description="Break duration in minutes")
    travel_time_minutes: int = Field(..., ge=0, description="Travel time in minutes")
    location: Literal["remote", "onsite"] = Field(..., description="Work location")
    notes: Optional[str] = Field(None, description="Optional notes")
    is_overnight: bool = Field(False, description="Whether shift spans midnight")

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

    @model_validator(mode="after")
    def validate_time_logic(self) -> "TimesheetEntry":
        """Validate time-related business rules.

        Validates:
        - end_time must be after start_time (unless overnight)
        - break_minutes must not exceed total work time

        Returns:
            The validated model instance

        Raises:
            ValueError: If validation fails
        """
        # Calculate work duration
        if self.is_overnight:
            # For overnight shifts, calculate across midnight
            # e.g., 22:00 to 06:00 = 8 hours
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            work_minutes = (24 * 60 - start_minutes) + end_minutes
        else:
            # Normal shift validation
            if self.end_time <= self.start_time:
                raise ValueError(
                    f"end_time ({self.end_time}) must be after start_time "
                    f"({self.start_time}). For overnight shifts, set "
                    f"is_overnight=True."
                )
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            work_minutes = end_minutes - start_minutes

        # Validate break time
        if self.break_minutes >= work_minutes:
            raise ValueError(
                f"break_minutes ({self.break_minutes}) must be less than "
                f"total work time ({work_minutes} minutes)"
            )

        return self
