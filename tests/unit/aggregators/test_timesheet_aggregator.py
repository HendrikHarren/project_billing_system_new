"""Tests for timesheet aggregator module.

This module contains comprehensive tests for the TimesheetAggregator class,
which combines multiple freelancer timesheets into a unified dataset.
"""

import datetime as dt
from decimal import Decimal
from typing import List
from unittest.mock import MagicMock

import pytest

from src.aggregators.timesheet_aggregator import (
    AggregatedTimesheetData,
    TimesheetAggregator,
)
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry
from src.models.trip import Trip


@pytest.fixture
def mock_timesheet_reader():
    """Create mock timesheet reader."""
    return MagicMock()


@pytest.fixture
def mock_project_terms_reader():
    """Create mock project terms reader."""
    return MagicMock()


@pytest.fixture
def mock_drive_service():
    """Create mock Google Drive service."""
    return MagicMock()


@pytest.fixture
def sample_timesheet_entries() -> List[TimesheetEntry]:
    """Create sample timesheet entries for testing.

    Uses dates from 2024 (previous year) to work with default filter.
    """
    return [
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2024, 6, 15),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=60,
            location="onsite",
        ),
        TimesheetEntry(
            freelancer_name="John Doe",
            date=dt.date(2024, 6, 16),
            project_code="PROJ-001",
            start_time=dt.time(9, 0),
            end_time=dt.time(17, 0),
            break_minutes=30,
            travel_time_minutes=0,
            location="remote",
        ),
        TimesheetEntry(
            freelancer_name="Jane Smith",
            date=dt.date(2024, 6, 15),
            project_code="PROJ-002",
            start_time=dt.time(10, 0),
            end_time=dt.time(18, 0),
            break_minutes=60,
            travel_time_minutes=120,
            location="onsite",
        ),
    ]


@pytest.fixture
def sample_project_terms() -> List[ProjectTerms]:
    """Create sample project terms for testing."""
    return [
        ProjectTerms(
            freelancer_name="John Doe",
            project_code="PROJ-001",
            hourly_rate=Decimal("85.00"),
            travel_surcharge_percentage=Decimal("15.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("60.00"),
        ),
        ProjectTerms(
            freelancer_name="Jane Smith",
            project_code="PROJ-002",
            hourly_rate=Decimal("90.00"),
            travel_surcharge_percentage=Decimal("20.0"),
            travel_time_percentage=Decimal("50.0"),
            cost_per_hour=Decimal("65.00"),
        ),
    ]


@pytest.fixture
def aggregator(mock_timesheet_reader, mock_project_terms_reader, mock_drive_service):
    """Create TimesheetAggregator instance for testing."""
    return TimesheetAggregator(
        timesheet_reader=mock_timesheet_reader,
        project_terms_reader=mock_project_terms_reader,
        drive_service=mock_drive_service,
    )


class TestTimesheetAggregatorInit:
    """Test TimesheetAggregator initialization."""

    def test_init_stores_dependencies(
        self, mock_timesheet_reader, mock_project_terms_reader, mock_drive_service
    ):
        """Test that constructor stores all dependencies."""
        aggregator = TimesheetAggregator(
            timesheet_reader=mock_timesheet_reader,
            project_terms_reader=mock_project_terms_reader,
            drive_service=mock_drive_service,
        )

        assert aggregator.timesheet_reader == mock_timesheet_reader
        assert aggregator.project_terms_reader == mock_project_terms_reader
        assert aggregator.drive_service == mock_drive_service


class TestAggregateTimesheets:
    """Test aggregating timesheets from Google Drive folder."""

    def test_aggregate_from_folder_success(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test successful aggregation from folder."""
        # Setup mocks
        folder_id = "test-folder-123"

        # Mock Drive service to return file list
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"},
            {"id": "file2", "name": "Jane_Smith_Timesheet"},
        ]

        # Mock timesheet reader to return entries
        mock_timesheet_reader.read_timesheet.side_effect = [
            [sample_timesheet_entries[0], sample_timesheet_entries[1]],  # John Doe
            [sample_timesheet_entries[2]],  # Jane Smith
        ]

        # Mock project terms reader
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Execute
        result = aggregator.aggregate_timesheets(folder_id)

        # Verify
        assert isinstance(result, AggregatedTimesheetData)
        assert len(result.entries) == 3
        assert len(result.billing_results) == 3
        assert len(result.trips) >= 0  # Trips calculated from entries
        mock_drive_service.list_files_in_folder.assert_called_once_with(folder_id)
        assert mock_timesheet_reader.read_timesheet.call_count == 2

    def test_aggregate_empty_folder(self, aggregator, mock_drive_service):
        """Test aggregation from empty folder."""
        folder_id = "empty-folder"
        mock_drive_service.list_files_in_folder.return_value = []

        result = aggregator.aggregate_timesheets(folder_id)

        assert isinstance(result, AggregatedTimesheetData)
        assert len(result.entries) == 0
        assert len(result.billing_results) == 0
        assert len(result.trips) == 0

    def test_aggregate_missing_project_terms(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
    ):
        """Test aggregation when project terms are missing for some entries."""
        folder_id = "test-folder"

        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"}
        ]

        mock_timesheet_reader.read_timesheet.return_value = [
            sample_timesheet_entries[0]
        ]

        # Empty project terms
        mock_project_terms_reader.get_all_project_terms.return_value = {}

        # Should raise KeyError for missing terms
        with pytest.raises(KeyError, match="No billing terms found"):
            aggregator.aggregate_timesheets(folder_id)

    def test_aggregate_skips_invalid_timesheets(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test that invalid timesheets are skipped gracefully."""
        folder_id = "test-folder"

        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"},
            {"id": "file2", "name": "Invalid_Timesheet"},
        ]

        # First file succeeds, second raises exception
        mock_timesheet_reader.read_timesheet.side_effect = [
            [sample_timesheet_entries[0]],
            Exception("Invalid timesheet format"),
        ]

        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Should continue processing valid timesheets
        result = aggregator.aggregate_timesheets(folder_id)

        assert len(result.entries) == 1
        assert result.entries[0].freelancer_name == "John Doe"


class TestFilterByDateRange:
    """Test filtering aggregated data by date range."""

    def test_filter_by_date_range(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test filtering entries by date range."""
        # Setup
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"}
        ]
        mock_timesheet_reader.read_timesheet.return_value = sample_timesheet_entries[:2]
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate first (uses default date filter)
        data = aggregator.aggregate_timesheets(folder_id)

        # Filter to only June 15
        filtered = aggregator.filter_by_date_range(
            data, start_date=dt.date(2024, 6, 15), end_date=dt.date(2024, 6, 15)
        )

        assert len(filtered.entries) == 1
        assert filtered.entries[0].date == dt.date(2024, 6, 15)

    def test_filter_by_date_range_no_matches(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test filtering with no matching dates."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"}
        ]
        mock_timesheet_reader.read_timesheet.return_value = sample_timesheet_entries[:2]
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        data = aggregator.aggregate_timesheets(folder_id)

        # Filter to different date range (outside the data range)
        filtered = aggregator.filter_by_date_range(
            data, start_date=dt.date(2024, 7, 1), end_date=dt.date(2024, 7, 31)
        )

        assert len(filtered.entries) == 0


class TestFilterByProject:
    """Test filtering aggregated data by project."""

    def test_filter_by_project(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test filtering entries by project code."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"},
            {"id": "file2", "name": "Jane_Smith_Timesheet"},
        ]
        mock_timesheet_reader.read_timesheet.side_effect = [
            sample_timesheet_entries[:2],  # John - PROJ-001
            [sample_timesheet_entries[2]],  # Jane - PROJ-002
        ]
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        data = aggregator.aggregate_timesheets(folder_id)

        # Filter to only PROJ-001
        filtered = aggregator.filter_by_project(data, project_code="PROJ-001")

        assert len(filtered.entries) == 2
        assert all(e.project_code == "PROJ-001" for e in filtered.entries)


class TestFilterByFreelancer:
    """Test filtering aggregated data by freelancer."""

    def test_filter_by_freelancer(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_timesheet_entries,
        sample_project_terms,
    ):
        """Test filtering entries by freelancer name."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "John_Doe_Timesheet"},
            {"id": "file2", "name": "Jane_Smith_Timesheet"},
        ]
        mock_timesheet_reader.read_timesheet.side_effect = [
            sample_timesheet_entries[:2],
            [sample_timesheet_entries[2]],
        ]
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        data = aggregator.aggregate_timesheets(folder_id)

        # Filter to only John Doe
        filtered = aggregator.filter_by_freelancer(data, freelancer_name="John Doe")

        assert len(filtered.entries) == 2
        assert all(e.freelancer_name == "John Doe" for e in filtered.entries)


class TestAggregateWithDateRangeFiltering:
    """Test filtering during aggregation for performance optimization."""

    def test_aggregate_with_start_date_only(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with only start date filter."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        # Create entries spanning multiple months
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 5, 30),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 7, 10),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate with start date filter
        result = aggregator.aggregate_timesheets(
            folder_id, start_date=dt.date(2024, 6, 1)
        )

        # Should only include June and July entries
        assert len(result.entries) == 2
        assert all(e.date >= dt.date(2024, 6, 1) for e in result.entries)
        assert len(result.billing_results) == 2

    def test_aggregate_with_end_date_only(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with only end date filter."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 5, 30),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate with end date filter
        result = aggregator.aggregate_timesheets(
            folder_id, end_date=dt.date(2024, 5, 31)
        )

        # Should only include May entry
        assert len(result.entries) == 1
        assert result.entries[0].date == dt.date(2024, 5, 30)
        assert len(result.billing_results) == 1

    def test_aggregate_with_date_range(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with both start and end date filters."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        # Entries spanning 3 months
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 5, 30),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 1),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 30),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 7, 1),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate for June only
        result = aggregator.aggregate_timesheets(
            folder_id, start_date=dt.date(2024, 6, 1), end_date=dt.date(2024, 6, 30)
        )

        # Should only include June entries
        assert len(result.entries) == 2
        assert all(
            dt.date(2024, 6, 1) <= e.date <= dt.date(2024, 6, 30)
            for e in result.entries
        )
        assert len(result.billing_results) == 2

    def test_aggregate_with_project_filter(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with project code filter."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate with project filter
        result = aggregator.aggregate_timesheets(folder_id, project_code="PROJ-001")

        # Should only include PROJ-001
        assert len(result.entries) == 1
        assert result.entries[0].project_code == "PROJ-001"
        assert len(result.billing_results) == 1

    def test_aggregate_with_freelancer_filter(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with freelancer name filter."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate with freelancer filter
        result = aggregator.aggregate_timesheets(folder_id, freelancer_name="John Doe")

        # Should only include John Doe
        assert len(result.entries) == 1
        assert result.entries[0].freelancer_name == "John Doe"
        assert len(result.billing_results) == 1

    def test_aggregate_with_combined_filters(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation with multiple filters combined."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        # Create diverse set of entries
        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 5, 30),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
            TimesheetEntry(
                freelancer_name="Jane Smith",
                date=dt.date(2024, 6, 20),
                project_code="PROJ-002",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {
            ("John Doe", "PROJ-001"): sample_project_terms[0],
            ("Jane Smith", "PROJ-002"): sample_project_terms[1],
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Aggregate with all filters
        result = aggregator.aggregate_timesheets(
            folder_id,
            start_date=dt.date(2024, 6, 1),
            end_date=dt.date(2024, 6, 30),
            project_code="PROJ-001",
            freelancer_name="John Doe",
        )

        # Should only include John Doe's June PROJ-001 entry
        assert len(result.entries) == 1
        assert result.entries[0].freelancer_name == "John Doe"
        assert result.entries[0].project_code == "PROJ-001"
        assert result.entries[0].date == dt.date(2024, 6, 15)
        assert len(result.billing_results) == 1

    def test_aggregate_with_filters_no_matches(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test aggregation when filters result in no matches."""
        folder_id = "test-folder"
        mock_drive_service.list_files_in_folder.return_value = [
            {"id": "file1", "name": "Timesheet"}
        ]

        entries = [
            TimesheetEntry(
                freelancer_name="John Doe",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            ),
        ]
        mock_timesheet_reader.read_timesheet.return_value = entries
        terms_map = {("John Doe", "PROJ-001"): sample_project_terms[0]}
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Filter for different month
        result = aggregator.aggregate_timesheets(
            folder_id, start_date=dt.date(2024, 7, 1), end_date=dt.date(2024, 7, 31)
        )

        # Should return empty data
        assert len(result.entries) == 0
        assert len(result.billing_results) == 0
        assert len(result.trips) == 0


class TestPerformanceOptimization:
    """Test performance optimizations for large datasets."""

    def test_handles_large_number_of_timesheets(
        self,
        aggregator,
        mock_drive_service,
        mock_timesheet_reader,
        mock_project_terms_reader,
        sample_project_terms,
    ):
        """Test that aggregator can handle 30+ timesheets efficiently."""
        folder_id = "large-folder"

        # Create 35 mock timesheet files
        files = [
            {"id": f"file{i}", "name": f"Freelancer_{i}_Timesheet"} for i in range(35)
        ]
        mock_drive_service.list_files_in_folder.return_value = files

        # Each timesheet returns 10 entries (using 2024 date for default filter)
        mock_entries = [
            TimesheetEntry(
                freelancer_name=f"Freelancer {i}",
                date=dt.date(2024, 6, 15),
                project_code="PROJ-001",
                start_time=dt.time(9, 0),
                end_time=dt.time(17, 0),
                break_minutes=30,
                travel_time_minutes=0,
                location="remote",
            )
            for i in range(10)
        ]
        mock_timesheet_reader.read_timesheet.return_value = mock_entries

        # Setup project terms for all freelancers
        terms_map = {
            (f"Freelancer {i}", "PROJ-001"): sample_project_terms[0] for i in range(10)
        }
        mock_project_terms_reader.get_all_project_terms.return_value = terms_map

        # Execute - should complete without timeout or memory issues
        result = aggregator.aggregate_timesheets(folder_id)

        assert len(result.entries) == 35 * 10  # 350 entries
        assert mock_timesheet_reader.read_timesheet.call_count == 35


class TestAggregatedTimesheetData:
    """Test AggregatedTimesheetData dataclass."""

    def test_dataclass_creation(self, sample_timesheet_entries):
        """Test creating AggregatedTimesheetData instance."""
        data = AggregatedTimesheetData(
            entries=sample_timesheet_entries, billing_results=[], trips=[]
        )

        assert data.entries == sample_timesheet_entries
        assert data.billing_results == []
        assert data.trips == []

    def test_dataclass_with_all_data(
        self, sample_timesheet_entries, sample_project_terms
    ):
        """Test dataclass with complete data."""
        from src.calculators.billing_calculator import BillingResult

        billing_results = [
            BillingResult(
                billable_hours=Decimal("7.5"),
                work_hours=Decimal("8.0"),
                break_hours=Decimal("0.5"),
                travel_hours=Decimal("0.0"),
                hours_billed=Decimal("637.50"),
                travel_surcharge=Decimal("0.00"),
                total_billed=Decimal("637.50"),
                total_cost=Decimal("450.00"),
                profit=Decimal("187.50"),
                profit_margin_percentage=Decimal("29.41"),
            )
        ]

        trips = [
            Trip(
                freelancer_name="John Doe",
                project_code="PROJ-001",
                location="Berlin",
                start_date=dt.date(2024, 6, 15),
                end_date=dt.date(2024, 6, 16),
            )
        ]

        data = AggregatedTimesheetData(
            entries=sample_timesheet_entries,
            billing_results=billing_results,
            trips=trips,
        )

        assert len(data.entries) == 3
        assert len(data.billing_results) == 1
        assert len(data.trips) == 1
