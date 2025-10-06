"""
Integration test fixtures and configuration.

This module provides fixtures for integration tests that interact with real
Google APIs and test end-to-end workflows.
"""

import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.config import BillingSystemConfig, get_config
from src.services import GoogleDriveService, GoogleSheetsService, SheetsCacheService


@pytest.fixture(scope="session")
def integration_config() -> BillingSystemConfig:
    """
    Get configuration for integration tests.

    This fixture uses real environment variables for Google API access.
    Tests marked with @pytest.mark.integration will be skipped if
    required environment variables are not set.
    """
    config = get_config()

    # Verify required environment variables are set
    required_vars = [
        "GOOGLE_PROJECT_ID",
        "GOOGLE_PRIVATE_KEY",
        "GOOGLE_CLIENT_EMAIL",
        "TIMESHEET_FOLDER_ID",
        "PROJECT_TERMS_FILE_ID",
        "MONTHLY_INVOICING_FOLDER_ID",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(
            f"Integration tests require environment variables: {', '.join(missing_vars)}"
        )

    return config


@pytest.fixture(scope="session")
def real_sheets_service(integration_config: BillingSystemConfig) -> GoogleSheetsService:
    """
    Create a real Google Sheets service for integration testing.

    Returns:
        GoogleSheetsService: Real Sheets service with API access
    """
    return GoogleSheetsService(config=integration_config)


@pytest.fixture(scope="session")
def real_drive_service(integration_config: BillingSystemConfig) -> GoogleDriveService:
    """
    Create a real Google Drive service for integration testing.

    Returns:
        GoogleDriveService: Real Drive service with API access
    """
    return GoogleDriveService(config=integration_config)


@pytest.fixture(scope="session")
def real_cache_service(integration_config: BillingSystemConfig) -> SheetsCacheService:
    """
    Create a real cache service for integration testing.

    Returns:
        SheetsCacheService: Real cache service with disk persistence
    """
    # Use a temporary cache file for integration tests
    temp_dir = tempfile.mkdtemp()
    cache_path = Path(temp_dir) / "integration_test_cache.json"

    service = SheetsCacheService(
        config=integration_config, cache_file_path=str(cache_path)
    )

    yield service

    # Cleanup cache file after tests
    if cache_path.exists():
        cache_path.unlink()
    if Path(temp_dir).exists():
        Path(temp_dir).rmdir()


@pytest.fixture
def test_spreadsheet_id(
    real_sheets_service: GoogleSheetsService, integration_config: BillingSystemConfig
) -> str:
    """
    Create a temporary test spreadsheet for integration testing.

    This fixture creates a new spreadsheet in Google Sheets and returns its ID.
    The spreadsheet is automatically cleaned up after the test.

    Returns:
        str: Spreadsheet ID for testing
    """
    # Create a test spreadsheet
    title = f"Integration Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}"

    spreadsheet_id = real_sheets_service.create_spreadsheet(
        title=title, folder_id=integration_config.monthly_invoicing_folder_id
    )

    yield spreadsheet_id

    # Cleanup: Move to trash or delete
    try:
        drive_service = GoogleDriveService(config=integration_config)
        drive_service.trash_file(spreadsheet_id)
    except Exception as e:
        print(f"Warning: Failed to cleanup test spreadsheet {spreadsheet_id}: {e}")


@pytest.fixture
def cleanup_test_files_list() -> List[str]:
    """
    Track test files created during integration tests for cleanup.

    Returns:
        List[str]: List of file IDs to cleanup after test
    """
    file_ids = []
    yield file_ids

    # Cleanup all tracked files
    if file_ids:
        from src.config import get_config
        from src.services import GoogleDriveService

        config = get_config()
        drive_service = GoogleDriveService(config=config)

        for file_id in file_ids:
            try:
                drive_service.trash_file(file_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup file {file_id}: {e}")


@pytest.fixture
def performance_baseline() -> Dict[str, float]:
    """
    Performance baseline metrics for comparison.

    These baselines are approximate and should be updated based on
    actual performance measurements.

    Returns:
        Dict[str, float]: Performance baseline metrics
    """
    return {
        "single_timesheet_read_ms": 500,  # 500ms max for single read
        "aggregation_10_timesheets_sec": 5.0,  # 5 seconds max for 10 timesheets
        "aggregation_30_timesheets_sec": 15.0,  # 15 seconds max for 30 timesheets
        "master_generation_1000_rows_sec": 2.0,  # 2 seconds max for 1000 rows
        "cache_hit_speedup_factor": 10.0,  # Cache should be 10x faster
        "api_call_reduction_percent": 60.0,  # 60% minimum API call reduction
    }


@pytest.fixture
def sample_integration_timesheet_data() -> List[List[Any]]:
    """
    Sample timesheet data for integration testing with realistic scenarios.

    Returns:
        List[List[Any]]: Timesheet data with headers and multiple entries
    """
    return [
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
        [
            "2024-10-01",
            "P&C_NEWRETAIL",
            "Off-site",
            "09:00",
            "17:00",
            "Development work",
            "00:30",
            "00:00",
        ],
        [
            "2024-10-02",
            "P&C_NEWRETAIL",
            "On-site",
            "08:00",
            "18:00",
            "Client meeting",
            "01:00",
            "02:00",
        ],
        [
            "2024-10-03",
            "P&C_NEWRETAIL",
            "On-site",
            "08:30",
            "17:30",
            "Workshop",
            "00:45",
            "01:30",
        ],
        [
            "2024-10-04",
            "PROJECT_ALPHA",
            "Off-site",
            "10:00",
            "18:00",
            "Code review",
            "01:00",
            "00:00",
        ],
        [
            "2024-10-07",
            "PROJECT_ALPHA",
            "Off-site",
            "09:30",
            "17:30",
            "Bug fixes",
            "00:30",
            "00:00",
        ],
    ]


@pytest.fixture
def sample_integration_project_terms() -> List[List[Any]]:
    """
    Sample project terms data for integration testing.

    Returns:
        List[List[Any]]: Project terms data with headers and entries
    """
    return [
        [
            "Project",
            "Consultant_ID",
            "Name",
            "Rate",
            "Cost",
            "Share of travel as work",
            "surcharge for travel",
        ],
        ["P&C_NEWRETAIL", "C001", "Test Freelancer", 85.0, 60.0, 0.5, 0.15],
        ["PROJECT_ALPHA", "C001", "Test Freelancer", 90.0, 65.0, 0.5, 0.10],
    ]


@pytest.fixture
def wait_for_api_rate_limit():
    """
    Wait fixture to avoid hitting Google API rate limits during tests.

    Use this fixture when running multiple API-heavy tests in sequence.
    """

    def wait(seconds: float = 1.0):
        """Wait for specified seconds to avoid rate limiting."""
        time.sleep(seconds)

    return wait


# Configure integration test collection
def pytest_collection_modifyitems(config, items):
    """
    Modify test collection for integration tests.

    - Add 'slow' marker to all integration tests
    - Add 'api' marker to tests that use real Google APIs
    """
    for item in items:
        # All integration tests are slow
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)

            # Add api marker for tests using real services
            if any(
                fixture in item.fixturenames
                for fixture in [
                    "real_sheets_service",
                    "real_drive_service",
                    "real_cache_service",
                ]
            ):
                item.add_marker(pytest.mark.api)
