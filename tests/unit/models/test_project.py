"""Unit tests for Project and ProjectTerms models."""
from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestProjectModel:
    """Test Project model creation and validation."""

    def test_create_valid_project(self):
        """Test creating a project with valid data."""
        from src.models.project import Project

        project = Project(code="PROJ-001", name="Website Redesign", client="Acme Corp")

        assert project.code == "PROJ-001"
        assert project.name == "Website Redesign"
        assert project.client == "Acme Corp"

    def test_empty_project_code_raises_error(self):
        """Test that empty project code raises validation error."""
        from src.models.project import Project

        with pytest.raises(ValidationError) as exc_info:
            Project(code="", name="Test", client="Client")

        assert "code" in str(exc_info.value).lower()

    def test_empty_project_name_raises_error(self):
        """Test that empty project name raises validation error."""
        from src.models.project import Project

        with pytest.raises(ValidationError) as exc_info:
            Project(code="PROJ-001", name="", client="Client")

        assert "name" in str(exc_info.value).lower()

    def test_empty_client_raises_error(self):
        """Test that empty client raises validation error."""
        from src.models.project import Project

        with pytest.raises(ValidationError) as exc_info:
            Project(code="PROJ-001", name="Test", client="")

        assert "client" in str(exc_info.value).lower()

    def test_project_serialization(self):
        """Test that project can be serialized to dict."""
        from src.models.project import Project

        project = Project(code="PROJ-002", name="Mobile App", client="Beta Inc")

        data = project.model_dump()
        assert data["code"] == "PROJ-002"
        assert data["name"] == "Mobile App"
        assert data["client"] == "Beta Inc"


class TestProjectTermsModel:
    """Test ProjectTerms model creation and validation."""

    def test_create_valid_project_terms(self):
        """Test creating project terms with valid data."""
        from src.models.project import ProjectTerms

        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        assert terms.freelancer_name == "John Doe"
        assert terms.project_code == "PROJ-001"
        assert terms.hourly_rate == Decimal("85.00")
        assert terms.travel_surcharge_percentage == Decimal("15.0")
        assert terms.travel_time_percentage == Decimal("50.0")
        assert terms.cost_per_hour == Decimal("60.00")

    def test_zero_hourly_rate_raises_error(self):
        """Test that zero hourly rate raises validation error."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("0"),
                travel_surcharge_percentage=Decimal("15.0"),
                travel_time_percentage=Decimal("50.0"),
                cost_per_hour=Decimal("60.00"),
            )

        assert "hourly_rate" in str(exc_info.value).lower()

    def test_negative_hourly_rate_raises_error(self):
        """Test that negative hourly rate raises validation error."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("-85.00"),
                travel_surcharge_percentage=Decimal("15.0"),
                travel_time_percentage=Decimal("50.0"),
                cost_per_hour=Decimal("60.00"),
            )

        assert "hourly_rate" in str(exc_info.value).lower()

    def test_negative_cost_raises_error(self):
        """Test that negative cost raises validation error."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("85.00"),
                travel_surcharge_percentage=Decimal("15.0"),
                travel_time_percentage=Decimal("50.0"),
                cost_per_hour=Decimal("-60.00"),
            )

        assert "cost_per_hour" in str(exc_info.value).lower()

    def test_percentage_over_100_raises_error(self):
        """Test that percentage over 100 raises validation error."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("85.00"),
                travel_surcharge_percentage=Decimal("150.0"),  # Invalid
                travel_time_percentage=Decimal("50.0"),
                cost_per_hour=Decimal("60.00"),
            )

        error_msg = str(exc_info.value).lower()
        assert "travel_surcharge_percentage" in error_msg or "percentage" in error_msg

    def test_negative_percentage_raises_error(self):
        """Test that negative percentage raises validation error."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("85.00"),
                travel_surcharge_percentage=Decimal("15.0"),
                travel_time_percentage=Decimal("-50.0"),  # Invalid
                cost_per_hour=Decimal("60.00"),
            )

        error_msg = str(exc_info.value).lower()
        assert "travel_time_percentage" in error_msg or "percentage" in error_msg

    def test_cost_exceeds_rate_raises_warning(self):
        """Test that cost exceeding rate raises validation error (no profit)."""
        from src.models.project import ProjectTerms

        with pytest.raises(ValidationError) as exc_info:
            ProjectTerms(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                hourly_rate=Decimal("60.00"),
                travel_surcharge_percentage=Decimal("15.0"),
                travel_time_percentage=Decimal("50.0"),
                cost_per_hour=Decimal("85.00"),  # Higher than rate!
            )

        error_msg = str(exc_info.value).lower()
        assert "cost" in error_msg or "profit" in error_msg or "rate" in error_msg

    def test_float_values_converted_to_decimal(self):
        """Test that float values are converted to Decimal."""
        from src.models.project import ProjectTerms

        terms = ProjectTerms(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            hourly_rate=85.0,  # Float instead of Decimal
            travel_surcharge_percentage=15.0,
            travel_time_percentage=50.0,
            cost_per_hour=60.0,
        )

        assert isinstance(terms.hourly_rate, Decimal)
        assert isinstance(terms.cost_per_hour, Decimal)

    def test_string_values_converted_to_decimal(self):
        """Test that string values are converted to Decimal."""
        from src.models.project import ProjectTerms

        terms = ProjectTerms(
            freelancer_name="Alice Brown",
            project_code="PROJ-003",
            hourly_rate="90.50",  # String instead of Decimal
            travel_surcharge_percentage="20.0",
            travel_time_percentage="75.0",
            cost_per_hour="65.25",
        )

        assert terms.hourly_rate == Decimal("90.50")
        assert terms.cost_per_hour == Decimal("65.25")

    def test_project_terms_serialization(self):
        """Test that project terms can be serialized to dict."""
        from src.models.project import ProjectTerms

        terms = ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        )

        data = terms.model_dump()
        assert data["freelancer_name"] == "John Doe"
        assert data["project_code"] == "PROJ-001"
        assert data["hourly_rate"] == Decimal("85.00")

    def test_zero_percentages_allowed(self):
        """Test that zero percentages are valid."""
        from src.models.project import ProjectTerms

        terms = ProjectTerms(
            freelancer_name="Remote Worker",
            project_code="PROJ-004",
            hourly_rate=Decimal("75.00"),
            travel_surcharge_percentage=Decimal("0"),  # No surcharge
            travel_time_percentage=Decimal("0"),  # No travel time
            cost_per_hour=Decimal("50.00"),
        )

        assert terms.travel_surcharge_percentage == Decimal("0")
        assert terms.travel_time_percentage == Decimal("0")
