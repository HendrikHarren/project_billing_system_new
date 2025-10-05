"""Unit tests for ProjectTermsReader."""

import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.readers.project_terms_reader import ProjectTermsReader


class TestProjectTermsReader:
    """Test ProjectTermsReader functionality."""

    @pytest.fixture
    def mock_sheets_service(self):
        """Create a mock Google Sheets service."""
        return Mock()

    @pytest.fixture
    def project_terms_reader(self, mock_sheets_service):
        """Create a ProjectTermsReader instance with mocked service."""
        return ProjectTermsReader(
            mock_sheets_service, spreadsheet_id="test-spreadsheet-id"
        )

    @pytest.fixture
    def sample_main_terms_data(self):
        """Sample project terms data from Google Sheets (actual column names)."""
        return pd.DataFrame(
            [
                {
                    "Project": "PROJ-001",
                    "Consultant_ID": "1",
                    "Name": "John Doe",
                    "Rate": "85.00",
                    "Cost": "60.00",
                    "Share of travel as work": "0.5",
                },
                {
                    "Project": "PROJ-002",
                    "Consultant_ID": "2",
                    "Name": "Jane Smith",
                    "Rate": "90.00",
                    "Cost": "65.00",
                    "Share of travel as work": "1.0",
                },
                {
                    "Project": "PROJ-003",
                    "Consultant_ID": "1",
                    "Name": "John Doe",
                    "Rate": "95.00",
                    "Cost": "70.00",
                    "Share of travel as work": "0.5",
                },
            ]
        )

    @pytest.fixture
    def sample_trip_terms_data(self):
        """Sample trip terms data from Google Sheets."""
        return pd.DataFrame(
            [
                {
                    "Min Days": "1",
                    "Max Days": "2",
                    "Reimbursement Type": "Per Diem",
                    "Amount per Day": "50.00",
                },
                {
                    "Min Days": "3",
                    "Max Days": "7",
                    "Reimbursement Type": "Per Diem",
                    "Amount per Day": "45.00",
                },
                {
                    "Min Days": "8",
                    "Max Days": "999",
                    "Reimbursement Type": "Flat Rate",
                    "Amount per Day": "40.00",
                },
            ]
        )

    def test_init(self, mock_sheets_service):
        """Test ProjectTermsReader initialization."""
        reader = ProjectTermsReader(
            mock_sheets_service, spreadsheet_id="test-id", cache_ttl=1800
        )
        assert reader.sheets_service == mock_sheets_service
        assert reader.spreadsheet_id == "test-id"
        assert reader.cache_ttl == 1800
        assert reader._cache == {}
        assert reader._trip_terms_cache is None

    def test_init_with_default_cache_ttl(self, mock_sheets_service):
        """Test initialization with default cache TTL."""
        reader = ProjectTermsReader(mock_sheets_service, spreadsheet_id="test-id")
        assert reader.cache_ttl == 3600  # Default 1 hour

    def test_get_all_project_terms_reads_and_caches(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test getting all project terms reads from sheet and caches."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        terms_dict = project_terms_reader.get_all_project_terms()

        # Verify API was called
        mock_sheets_service.read_sheet.assert_called_once()

        # Verify correct number of terms
        assert len(terms_dict) == 3

        # Verify cache was populated
        assert len(project_terms_reader._cache) == 3

        # Verify data structure
        key = ("John Doe", "PROJ-001")
        assert key in terms_dict
        assert terms_dict[key].freelancer_name == "John Doe"
        assert terms_dict[key].project_code == "PROJ-001"
        assert terms_dict[key].hourly_rate == Decimal("85.00")
        assert terms_dict[key].travel_surcharge_percentage == Decimal("0")
        assert terms_dict[key].travel_time_percentage == Decimal("0.5")
        assert terms_dict[key].cost_per_hour == Decimal("60.00")

    def test_get_all_project_terms_uses_cache_on_second_call(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test that second call uses cache instead of reading sheet."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        # First call - should read from sheet
        terms1 = project_terms_reader.get_all_project_terms()

        # Second call - should use cache
        terms2 = project_terms_reader.get_all_project_terms()

        # Verify API was called only once
        assert mock_sheets_service.read_sheet.call_count == 1

        # Verify same data returned
        assert terms1 == terms2

    def test_get_project_terms_specific_freelancer_project(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test getting terms for specific freelancer and project."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        terms = project_terms_reader.get_project_terms("John Doe", "PROJ-001")

        assert terms.freelancer_name == "John Doe"
        assert terms.project_code == "PROJ-001"
        assert terms.hourly_rate == Decimal("85.00")

    def test_get_project_terms_not_found_returns_none(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test getting terms for non-existent combination returns None."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        terms = project_terms_reader.get_project_terms("Unknown", "PROJ-999")

        assert terms is None

    def test_get_project_terms_case_sensitive(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test that freelancer and project lookup is case-sensitive."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        terms = project_terms_reader.get_project_terms("john doe", "PROJ-001")

        assert terms is None

    def test_cache_expiration_triggers_refresh(
        self, mock_sheets_service, sample_main_terms_data
    ):
        """Test that expired cache triggers a refresh."""
        reader = ProjectTermsReader(
            mock_sheets_service, spreadsheet_id="test-id", cache_ttl=1  # 1 second TTL
        )
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        # First call
        reader.get_all_project_terms()
        assert mock_sheets_service.read_sheet.call_count == 1

        # Wait for cache to expire
        time.sleep(1.1)

        # Second call should refresh
        reader.get_all_project_terms()
        assert mock_sheets_service.read_sheet.call_count == 2

    def test_invalidate_cache_clears_cache(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test that invalidate_cache clears the cache."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        # Populate cache
        project_terms_reader.get_all_project_terms()
        assert len(project_terms_reader._cache) > 0

        # Invalidate cache
        project_terms_reader.invalidate_cache()

        assert len(project_terms_reader._cache) == 0
        assert project_terms_reader._trip_terms_cache is None
        assert project_terms_reader._cache_timestamp is None

    def test_get_trip_terms_reads_and_caches(
        self, project_terms_reader, mock_sheets_service, sample_trip_terms_data
    ):
        """Test getting trip terms reads from sheet and caches."""
        mock_sheets_service.read_sheet.return_value = sample_trip_terms_data

        trip_terms = project_terms_reader.get_trip_terms()

        # Verify API was called
        mock_sheets_service.read_sheet.assert_called_once()

        # Verify structure
        assert len(trip_terms) == 3
        assert trip_terms[0]["min_days"] == 1
        assert trip_terms[0]["max_days"] == 2
        assert trip_terms[0]["reimbursement_type"] == "Per Diem"
        assert trip_terms[0]["amount_per_day"] == Decimal("50.00")

    def test_get_trip_terms_uses_cache_on_second_call(
        self, project_terms_reader, mock_sheets_service, sample_trip_terms_data
    ):
        """Test that second call to get_trip_terms uses cache."""
        mock_sheets_service.read_sheet.return_value = sample_trip_terms_data

        # First call
        terms1 = project_terms_reader.get_trip_terms()

        # Second call
        terms2 = project_terms_reader.get_trip_terms()

        # Verify API was called only once
        assert mock_sheets_service.read_sheet.call_count == 1

        # Verify same data
        assert terms1 == terms2

    def test_parse_main_terms_row_valid_data(self, project_terms_reader):
        """Test parsing a valid main terms row."""
        row = {
            "Name": "John Doe",
            "Project": "PROJ-001",
            "Rate": "85.00",
            "_TravelSurcharge_REMOVED": "15.0",
            "Share of travel as work": "50.0",
            "Cost": "60.00",
        }

        terms = project_terms_reader._parse_main_terms_row(row)

        assert terms is not None
        assert terms.freelancer_name == "John Doe"
        assert terms.project_code == "PROJ-001"
        assert terms.hourly_rate == Decimal("85.00")

    def test_parse_main_terms_row_with_whitespace(self, project_terms_reader):
        """Test parsing row with whitespace in fields."""
        row = {
            "Name": " John Doe ",
            "Project": " PROJ-001 ",
            "Rate": " 85.00 ",
            "_TravelSurcharge_REMOVED": " 15.0 ",
            "Share of travel as work": " 50.0 ",
            "Cost": " 60.00 ",
        }

        terms = project_terms_reader._parse_main_terms_row(row)

        assert terms is not None
        assert terms.freelancer_name == "John Doe"
        assert terms.project_code == "PROJ-001"

    def test_parse_main_terms_row_missing_freelancer_returns_none(
        self, project_terms_reader
    ):
        """Test parsing row with missing freelancer returns None."""
        row = {
            "Name": "",
            "Project": "PROJ-001",
            "Rate": "85.00",
            "_TravelSurcharge_REMOVED": "15.0",
            "Share of travel as work": "50.0",
            "Cost": "60.00",
        }

        terms = project_terms_reader._parse_main_terms_row(row)
        assert terms is None

    def test_parse_main_terms_row_invalid_rate_returns_none(self, project_terms_reader):
        """Test parsing row with invalid rate returns None."""
        row = {
            "Name": "John Doe",
            "Project": "PROJ-001",
            "Rate": "invalid",
            "_TravelSurcharge_REMOVED": "15.0",
            "Share of travel as work": "50.0",
            "Cost": "60.00",
        }

        with patch("src.readers.project_terms_reader.logger") as mock_logger:
            terms = project_terms_reader._parse_main_terms_row(row)
            assert terms is None
            mock_logger.warning.assert_called()

    def test_parse_main_terms_row_cost_exceeds_rate_returns_none(
        self, project_terms_reader
    ):
        """Test parsing row where cost exceeds rate returns None."""
        row = {
            "Name": "John Doe",
            "Project": "PROJ-001",
            "Rate": "60.00",
            "_TravelSurcharge_REMOVED": "15.0",
            "Share of travel as work": "50.0",
            "Cost": "85.00",  # Cost > Rate
        }

        with patch("src.readers.project_terms_reader.logger") as mock_logger:
            terms = project_terms_reader._parse_main_terms_row(row)
            assert terms is None
            mock_logger.warning.assert_called()

    def test_parse_trip_terms_row_valid_data(self, project_terms_reader):
        """Test parsing a valid trip terms row."""
        row = {
            "Min Days": "1",
            "Max Days": "2",
            "Reimbursement Type": "Per Diem",
            "Amount per Day": "50.00",
        }

        trip_term = project_terms_reader._parse_trip_terms_row(row)

        assert trip_term is not None
        assert trip_term["min_days"] == 1
        assert trip_term["max_days"] == 2
        assert trip_term["reimbursement_type"] == "Per Diem"
        assert trip_term["amount_per_day"] == Decimal("50.00")

    def test_parse_trip_terms_row_with_whitespace(self, project_terms_reader):
        """Test parsing trip terms row with whitespace."""
        row = {
            "Min Days": " 3 ",
            "Max Days": " 7 ",
            "Reimbursement Type": " Per Diem ",
            "Amount per Day": " 45.00 ",
        }

        trip_term = project_terms_reader._parse_trip_terms_row(row)

        assert trip_term is not None
        assert trip_term["min_days"] == 3
        assert trip_term["reimbursement_type"] == "Per Diem"

    def test_parse_trip_terms_row_invalid_days_returns_none(self, project_terms_reader):
        """Test parsing trip terms row with invalid days returns None."""
        row = {
            "Min Days": "invalid",
            "Max Days": "2",
            "Reimbursement Type": "Per Diem",
            "Amount per Day": "50.00",
        }

        with patch("src.readers.project_terms_reader.logger") as mock_logger:
            trip_term = project_terms_reader._parse_trip_terms_row(row)
            assert trip_term is None
            mock_logger.warning.assert_called()

    def test_parse_trip_terms_row_missing_type_returns_none(self, project_terms_reader):
        """Test parsing trip terms row with missing type returns None."""
        row = {
            "Min Days": "1",
            "Max Days": "2",
            "Reimbursement Type": "",
            "Amount per Day": "50.00",
        }

        trip_term = project_terms_reader._parse_trip_terms_row(row)
        assert trip_term is None

    def test_read_main_terms_sheet_with_custom_sheet_name(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test reading main terms with custom sheet name."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        project_terms_reader._read_main_terms_sheet(sheet_name="CustomSheet")

        # Verify correct sheet name used
        call_args = mock_sheets_service.read_sheet.call_args
        assert "CustomSheet" in str(call_args)

    def test_read_trip_terms_sheet_with_custom_sheet_name(
        self, project_terms_reader, mock_sheets_service, sample_trip_terms_data
    ):
        """Test reading trip terms with custom sheet name."""
        mock_sheets_service.read_sheet.return_value = sample_trip_terms_data

        project_terms_reader._read_trip_terms_sheet(sheet_name="TripSheet")

        # Verify correct sheet name used
        call_args = mock_sheets_service.read_sheet.call_args
        assert "TripSheet" in str(call_args)

    def test_get_all_project_terms_empty_sheet(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test getting terms from empty sheet returns empty dict."""
        mock_sheets_service.read_sheet.return_value = pd.DataFrame()

        terms_dict = project_terms_reader.get_all_project_terms()

        assert terms_dict == {}

    def test_get_trip_terms_empty_sheet(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test getting trip terms from empty sheet returns empty list."""
        mock_sheets_service.read_sheet.return_value = pd.DataFrame()

        trip_terms = project_terms_reader.get_trip_terms()

        assert trip_terms == []

    def test_get_all_project_terms_handles_api_error(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test that API errors are propagated."""
        mock_sheets_service.read_sheet.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            project_terms_reader.get_all_project_terms()

    def test_get_trip_terms_handles_api_error(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test that trip terms API errors are propagated."""
        mock_sheets_service.read_sheet.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            project_terms_reader.get_trip_terms()

    def test_multiple_freelancers_same_project(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test handling multiple freelancers on same project."""
        data = pd.DataFrame(
            [
                {
                    "Name": "John Doe",
                    "Project": "PROJ-001",
                    "Rate": "85.00",
                    "_TravelSurcharge_REMOVED": "15.0",
                    "Share of travel as work": "50.0",
                    "Cost": "60.00",
                },
                {
                    "Name": "Jane Smith",
                    "Project": "PROJ-001",
                    "Rate": "90.00",
                    "_TravelSurcharge_REMOVED": "20.0",
                    "Share of travel as work": "100.0",
                    "Cost": "65.00",
                },
            ]
        )
        mock_sheets_service.read_sheet.return_value = data

        terms_dict = project_terms_reader.get_all_project_terms()

        assert len(terms_dict) == 2
        assert ("John Doe", "PROJ-001") in terms_dict
        assert ("Jane Smith", "PROJ-001") in terms_dict
        assert terms_dict[("John Doe", "PROJ-001")].hourly_rate == Decimal("85.00")
        assert terms_dict[("Jane Smith", "PROJ-001")].hourly_rate == Decimal("90.00")

    def test_decimal_precision_preserved(
        self, project_terms_reader, mock_sheets_service
    ):
        """Test that decimal precision is preserved."""
        data = pd.DataFrame(
            [
                {
                    "Name": "John Doe",
                    "Project": "PROJ-001",
                    "Rate": "85.50",
                    "_TravelSurcharge_REMOVED": "15.25",
                    "Share of travel as work": "50.75",
                    "Cost": "60.33",
                }
            ]
        )
        mock_sheets_service.read_sheet.return_value = data

        terms = project_terms_reader.get_project_terms("John Doe", "PROJ-001")

        assert terms.hourly_rate == Decimal("85.50")
        assert terms.travel_surcharge_percentage == Decimal("0")
        assert terms.travel_time_percentage == Decimal("50.75")
        assert terms.cost_per_hour == Decimal("60.33")

    def test_cache_timestamp_updated_on_read(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test that cache timestamp is updated when data is read."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        before = datetime.now()
        project_terms_reader.get_all_project_terms()
        after = datetime.now()

        assert project_terms_reader._cache_timestamp is not None
        assert before <= project_terms_reader._cache_timestamp <= after

    def test_get_project_terms_triggers_load_if_cache_empty(
        self, project_terms_reader, mock_sheets_service, sample_main_terms_data
    ):
        """Test that get_project_terms loads data if cache is empty."""
        mock_sheets_service.read_sheet.return_value = sample_main_terms_data

        # Cache should be empty initially
        assert len(project_terms_reader._cache) == 0

        # Getting specific terms should trigger load
        terms = project_terms_reader.get_project_terms("John Doe", "PROJ-001")

        assert terms is not None
        assert mock_sheets_service.read_sheet.call_count == 1
        assert len(project_terms_reader._cache) > 0
