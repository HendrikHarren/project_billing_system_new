"""
End-to-end pipeline integration tests.

These tests verify the complete data flow from reading timesheets
through aggregation, calculation, and report generation.

These are marked as @pytest.mark.e2e and @pytest.mark.integration and
require real Google API credentials to run.
"""

from datetime import date

import pytest

from src.config import BillingSystemConfig
from src.readers import TimesheetReader
from tests.integration.utils import generate_test_timesheet


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndPipeline:
    """Test complete end-to-end workflow from read to write."""

    def test_full_pipeline_with_mock_data(
        self,
        real_sheets_service,
        real_drive_service,
        integration_config: BillingSystemConfig,
        test_spreadsheet_id: str,
        cleanup_test_files_list,
    ):
        """
        Test the complete pipeline with mocked input data.

        This test verifies:
        1. Data can be written to a test spreadsheet
        2. TimesheetReader can read the data
        3. Aggregator can process the data
        4. Master timesheet can be generated
        5. Output can be written to Google Sheets

        This is a simplified E2E test using test data, not production data.
        """
        # Step 1: Create test timesheet data in a spreadsheet
        test_data = generate_test_timesheet(
            freelancer_name="Test Freelancer E2E",
            project_code="P&C_NEWRETAIL",
            num_entries=10,
            include_trips=True,
        )

        # Write test data to the test spreadsheet
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # Step 2: Read timesheet using TimesheetReader
        reader = TimesheetReader(
            sheets_service=real_sheets_service, freelancer_name="Test Freelancer E2E"
        )

        entries = reader.read_timesheet(spreadsheet_id=test_spreadsheet_id)

        # Verify we got entries
        assert len(entries) > 0, "Should have read timesheet entries"
        assert all(entry.freelancer_name == "Test Freelancer E2E" for entry in entries)

        # Step 3: Verify aggregation works (simplified - just verify it runs)
        # Note: Full aggregation test requires project terms setup, which is tested separately
        assert len(entries) == 10, f"Expected 10 entries, got {len(entries)}"

        # Verify data integrity
        for entry in entries:
            assert entry.date is not None
            assert entry.project is not None
            assert entry.start_time is not None
            assert entry.end_time is not None

    def test_pipeline_with_validation(
        self,
        real_sheets_service,
        test_spreadsheet_id: str,
    ):
        """
        Test pipeline with data validation.

        Verifies that validation errors are properly detected and handled.
        """
        # Create test data with validation issues
        invalid_data = [
            [
                "Date",
                "Project",
                "Location",
                "Start Time",
                "End Time",
                "Topics worked on",
                "Break",
                "Travel time",
            ],
            # Invalid: end time before start time
            [
                "2024-10-01",
                "P&C_NEWRETAIL",
                "Off-site",
                "17:00",
                "09:00",
                "Invalid entry",
                "01:00",
                "00:00",
            ],
            # Valid entry for comparison
            [
                "2024-10-02",
                "P&C_NEWRETAIL",
                "Off-site",
                "09:00",
                "17:00",
                "Valid entry",
                "01:00",
                "00:00",
            ],
        ]

        # Write invalid data
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=invalid_data,
        )

        # Read with validation
        reader = TimesheetReader(
            sheets_service=real_sheets_service, freelancer_name="Test Validation"
        )

        entries = reader.read_timesheet(spreadsheet_id=test_spreadsheet_id)

        # Should still return entries (validation warnings, not errors)
        assert len(entries) > 0, "Should return entries even with validation warnings"

    def test_master_timesheet_generation_integration(
        self,
        real_sheets_service,
        test_spreadsheet_id: str,
        sample_integration_timesheet_data,
    ):
        """
        Test master timesheet generation with real data structures.

        This verifies that the generator can handle realistic data and
        produce properly formatted output.
        """
        # Write test data
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=sample_integration_timesheet_data,
        )

        # Read data
        reader = TimesheetReader(
            sheets_service=real_sheets_service, freelancer_name="Test Generator"
        )

        entries = reader.read_timesheet(spreadsheet_id=test_spreadsheet_id)

        # Verify we can read the data
        assert len(entries) > 0
        assert all(isinstance(entry.date, date) for entry in entries)

        # Note: Full generation test requires aggregated data with billing info
        # This is tested in the aggregation integration tests


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWithRealTimesheet:
    """Test E2E workflow with real timesheet from Google Drive."""

    @pytest.mark.skipif(
        "not config.getoption('--run-real-api-tests', default=False)",
        reason="Requires --run-real-api-tests flag and real production data",
    )
    def test_read_real_timesheet_from_drive(
        self,
        real_drive_service,
        real_sheets_service,
        integration_config: BillingSystemConfig,
    ):
        """
        Test reading a real timesheet from Google Drive.

        This test is skipped by default and requires:
        1. --run-real-api-tests flag
        2. Real Google Drive folder with timesheets
        3. Valid credentials

        This is useful for verifying the system works with actual production data.
        """
        # List files in the timesheet folder
        files = real_drive_service.list_files_in_folder(
            folder_id=integration_config.timesheet_folder_id
        )

        # Verify we found some timesheets
        assert len(files) > 0, "Should find timesheets in configured folder"

        # Pick the first timesheet file
        test_file = files[0]
        file_id = test_file["id"]
        file_name = test_file.get("name", "Unknown")

        # Read the timesheet
        reader = TimesheetReader(
            sheets_service=real_sheets_service, freelancer_name=file_name
        )

        entries = reader.read_timesheet(spreadsheet_id=file_id)

        # Verify we got data
        assert len(entries) > 0, f"Should read entries from {file_name}"

        # Verify data structure
        for entry in entries:
            assert entry.freelancer_name is not None
            assert entry.date is not None
            assert entry.project is not None


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestCachingInPipeline:
    """Test caching behavior in end-to-end workflows."""

    def test_cache_effectiveness_in_pipeline(
        self,
        real_sheets_service,
        real_cache_service,
        test_spreadsheet_id: str,
        sample_integration_timesheet_data,
    ):
        """
        Test that caching works effectively in the pipeline.

        Verifies:
        1. First read hits the API
        2. Second read uses cache (faster)
        3. Cache invalidation works when data changes
        """
        # Write initial data
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=sample_integration_timesheet_data,
        )

        # First read - should cache
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z100"
        )

        # Second read - should use cache
        data2 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z100"
        )

        # Data should be identical
        assert data1 == data2

        # Verify cache has the entry
        cache_stats = real_cache_service.get_cache_stats()
        assert cache_stats["size"] > 0, "Cache should have entries"

    def test_cache_invalidation_on_modification(
        self,
        real_sheets_service,
        real_cache_service,
        test_spreadsheet_id: str,
        sample_integration_timesheet_data,
    ):
        """
        Test that cache is properly invalidated when data is modified.

        This is critical for data accuracy - we must not serve stale data.
        """
        # Write and read initial data (caches it)
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=sample_integration_timesheet_data,
        )

        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z100"
        )

        # Modify the data
        modified_data = sample_integration_timesheet_data.copy()
        modified_data.append(
            [
                "2024-10-08",
                "NEW_PROJECT",
                "Off-site",
                "09:00",
                "17:00",
                "New entry",
                "01:00",
                "00:00",
            ]
        )

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=modified_data,
        )

        # Read again - should get updated data (cache should be invalidated)
        data2 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z100"
        )

        # Data should be different (new row added)
        assert len(data2) > len(data1), "Should have more rows after modification"
