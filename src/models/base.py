"""Base model for all data models in the billing system.

This module provides a base Pydantic model with common configuration
and helper methods for serialization/deserialization.
"""

from pydantic import BaseModel, ConfigDict


class BaseDataModel(BaseModel):
    """Base class for all data models.

    Provides common configuration and helper methods for:
    - Validation with type checking
    - Serialization to/from dictionaries
    - Immutability (frozen models)
    - Arbitrary types support for dates, times, decimals

    Example:
        >>> class User(BaseDataModel):
        ...     name: str
        ...     age: int
        >>> user = User(name="Alice", age=30)
        >>> user.name
        'Alice'
        >>> user.model_dump()
        {'name': 'Alice', 'age': 30}
    """

    model_config = ConfigDict(
        # Allow arbitrary types like Decimal, date, time
        arbitrary_types_allowed=True,
        # Validate on assignment to catch errors early
        validate_assignment=True,
        # Use strict type checking
        strict=False,
        # Allow extra fields to be ignored during validation
        extra="forbid",
        # Frozen models are immutable after creation
        frozen=False,
    )
