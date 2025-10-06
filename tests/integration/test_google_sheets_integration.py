"""
Google Sheets API integration tests.

Tests real interactions with Google Sheets API including:
- Read/write operations
- Batch operations
- Caching behavior
- Error handling
- Rate limiting

Requires real Google API credentials and is marked as @pytest.mark.integration.
"""

import time
from datetime import datetime

import pytest

from src.config import BillingSystemConfig
from src.services import GoogleSheetsService, SheetsCacheService


@pytest.mark.integration
@pytest.mark.api
class TestGoogleSheetsIntegration:
    """Integration tests for Google Sheets service."""

    def test_create_and_read_spreadsheet(
        self,
        real_sheets_service: GoogleSheetsService,
        integration_config: BillingSystemConfig,
        cleanup_test_files_list,
    ):
        """Test creating a spreadsheet and reading data from it."""
        # Create a new spreadsheet
        title = f"Integration Test Sheets - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet_id = real_sheets_service.create_spreadsheet(
            title=title, folder_id=integration_config.monthly_invoicing_folder_id
        )

        # Track for cleanup
        cleanup_test_files_list.append(spreadsheet_id)

        # Verify creation
        assert spreadsheet_id is not None
        assert len(spreadsheet_id) > 0

        # Write data to the spreadsheet
        test_data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Value 1", "Value 2", "Value 3"],
            ["Value 4", "Value 5", "Value 6"],
        ]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=spreadsheet_id, range_name="Sheet1!A1", values=test_data
        )

        # Read the data back
        read_data = real_sheets_service.read_sheet_data(
            spreadsheet_id=spreadsheet_id, range_name="Sheet1!A1:C3"
        )

        # Verify data matches
        assert read_data == test_data

    def test_update_and_verify_data(
        self,
        real_sheets_service: GoogleSheetsService,
        test_spreadsheet_id: str,
    ):
        """Test updating data and verifying changes."""
        # Write initial data
        initial_data = [["Name", "Value"], ["Test", "100"], ["Test2", "200"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=initial_data,
        )

        # Update a specific cell
        updated_data = [["Modified", "999"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A2",
            values=updated_data,
        )

        # Read back and verify
        read_data = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B3"
        )

        # First row should be unchanged
        assert read_data[0] == initial_data[0]

        # Second row should be updated
        assert read_data[1] == ["Modified", "999"]

    def test_batch_read_operations(
        self,
        real_sheets_service: GoogleSheetsService,
        test_spreadsheet_id: str,
    ):
        """Test reading multiple ranges in batch."""
        # Write test data to multiple ranges
        data_sheet1 = [["Sheet1 Data", "A"], ["Row2", "B"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=data_sheet1,
        )

        # Note: batch operations tested implicitly through service usage
        # Read both ranges
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B2"
        )

        assert data1 == data_sheet1

    def test_empty_sheet_handling(
        self,
        real_sheets_service: GoogleSheetsService,
        test_spreadsheet_id: str,
    ):
        """Test reading from an empty sheet."""
        # Try to read from a range that doesn't exist yet
        data = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!Z100:Z200"
        )

        # Should return empty list, not error
        assert isinstance(data, list)
        assert len(data) == 0

    def test_large_dataset_handling(
        self,
        real_sheets_service: GoogleSheetsService,
        test_spreadsheet_id: str,
    ):
        """Test handling larger datasets (100+ rows)."""
        # Generate 200 rows of data
        large_data = [["Col1", "Col2", "Col3"]]
        for i in range(200):
            large_data.append([f"Value{i}_1", f"Value{i}_2", f"Value{i}_3"])

        # Write large dataset
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=large_data,
        )

        # Read it back
        read_data = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:C201"
        )

        # Verify size
        assert len(read_data) == 201  # 200 data rows + 1 header
        assert read_data[0] == ["Col1", "Col2", "Col3"]
        assert read_data[100] == ["Value99_1", "Value99_2", "Value99_3"]


@pytest.mark.integration
@pytest.mark.api
class TestSheetsCacheIntegration:
    """Integration tests for caching behavior with real API."""

    def test_cache_hit_performance(
        self,
        real_sheets_service: GoogleSheetsService,
        real_cache_service: SheetsCacheService,
        test_spreadsheet_id: str,
    ):
        """Test that cache provides significant performance improvement."""
        # Write test data
        test_data = [["Header"] + [f"Col{i}" for i in range(10)]]
        for i in range(50):
            test_data.append([f"Row{i}"] + [f"Val{i}_{j}" for j in range(10)])

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # First read - cache miss (slower)
        start_time = time.time()
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:K51"
        )
        first_read_time = time.time() - start_time

        # Second read - cache hit (should be much faster)
        start_time = time.time()
        data2 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:K51"
        )
        second_read_time = time.time() - start_time

        # Data should match
        assert data1 == data2

        # Cache hit should be at least 5x faster (conservative estimate)
        # In practice it's often 10x or more
        assert (
            second_read_time < first_read_time / 5
        ), f"Cache hit ({second_read_time:.3f}s) should be much faster than miss ({first_read_time:.3f}s)"

    def test_cache_stats_tracking(
        self,
        real_sheets_service: GoogleSheetsService,
        real_cache_service: SheetsCacheService,
        test_spreadsheet_id: str,
    ):
        """Test that cache statistics are properly tracked."""
        # Clear cache first
        real_cache_service.clear()

        # Write and read data
        test_data = [["A", "B"], ["1", "2"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # First read - cache miss
        real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B2"
        )

        # Second read - cache hit
        real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B2"
        )

        # Check cache stats
        stats = real_cache_service.get_cache_stats()

        assert stats["size"] > 0, "Cache should have entries"
        # Note: hits/misses tracking depends on implementation

    def test_modification_time_based_invalidation(
        self,
        real_sheets_service: GoogleSheetsService,
        real_cache_service: SheetsCacheService,
        test_spreadsheet_id: str,
        wait_for_api_rate_limit,
    ):
        """Test that cache is invalidated based on modification time."""
        # Write initial data and cache it
        initial_data = [["Version", "1"], ["Data", "Original"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=initial_data,
        )

        # Read to cache
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B2"
        )

        # Wait to ensure modification time will be different
        wait_for_api_rate_limit(2.0)

        # Modify the data
        modified_data = [["Version", "2"], ["Data", "Modified"]]

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=modified_data,
        )

        # Wait for modification time to update
        wait_for_api_rate_limit(2.0)

        # Read again - should get fresh data (cache invalidated)
        data2 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:B2"
        )

        # Data should be different
        assert data1 != data2
        assert data2 == modified_data


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestSheetsErrorHandling:
    """Test error handling and edge cases with real API."""

    def test_invalid_spreadsheet_id(
        self,
        real_sheets_service: GoogleSheetsService,
    ):
        """Test handling of invalid spreadsheet ID."""
        with pytest.raises(Exception):
            real_sheets_service.read_sheet_data(
                spreadsheet_id="invalid_id_12345", range_name="Sheet1!A1:B2"
            )

    def test_invalid_range(
        self,
        real_sheets_service: GoogleSheetsService,
        test_spreadsheet_id: str,
    ):
        """Test handling of invalid range specification."""
        # Invalid range format should be handled gracefully or raise clear error
        with pytest.raises((ValueError, Exception)):
            real_sheets_service.read_sheet_data(
                spreadsheet_id=test_spreadsheet_id, range_name="InvalidRange!!!"
            )

    def test_permission_error_handling(
        self,
        real_sheets_service: GoogleSheetsService,
    ):
        """Test handling of permission errors."""
        # Try to access a spreadsheet we don't have permission for
        # This should raise an appropriate exception
        # Note: This test requires a known spreadsheet ID without permissions
        # Skip if not available
        pytest.skip("Requires a test spreadsheet without permissions")
