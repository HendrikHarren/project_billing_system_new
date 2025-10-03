"""Unit tests for base model functionality."""

from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestBaseModelSerialization:
    """Test serialization/deserialization for models."""

    def test_model_can_be_created_with_valid_data(self):
        """Test that a simple model can be created with valid data."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

    def test_model_to_dict(self):
        """Test model serialization to dictionary."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        data = model.model_dump()
        assert data == {"name": "test", "value": 42}

    def test_model_from_dict(self):
        """Test model deserialization from dictionary."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            name: str
            value: int

        data = {"name": "test", "value": 42}
        model = TestModel.model_validate(data)
        assert model.name == "test"
        assert model.value == 42

    def test_model_handles_dates(self):
        """Test that models can handle date serialization."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            event_date: date

        model = TestModel(event_date=date(2023, 6, 15))
        assert model.event_date == date(2023, 6, 15)

    def test_model_handles_times(self):
        """Test that models can handle time serialization."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            event_time: time

        model = TestModel(event_time=time(14, 30))
        assert model.event_time == time(14, 30)

    def test_model_handles_decimals(self):
        """Test that models can handle Decimal types."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            amount: Decimal

        model = TestModel(amount=Decimal("123.45"))
        assert model.amount == Decimal("123.45")

    def test_model_validation_error_on_invalid_type(self):
        """Test that validation errors are raised for invalid types."""
        from src.models.base import BaseDataModel

        class TestModel(BaseDataModel):
            value: int

        with pytest.raises(ValidationError) as exc_info:
            TestModel(value="not an int")

        assert "validation error" in str(exc_info.value).lower()
