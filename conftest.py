"""
Global pytest configuration and fixtures.
"""
import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any
from src.config import BillingSystemConfig, reload_config


@pytest.fixture(scope="session")
def test_env_vars() -> Dict[str, str]:
    """Test environment variables for configuration."""
    return {
        'GOOGLE_PROJECT_ID': 'test-project',
        'GOOGLE_PRIVATE_KEY_ID': 'test-key-id',
        'GOOGLE_PRIVATE_KEY': '-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n',
        'GOOGLE_CLIENT_EMAIL': 'test@test.com',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_X509_CERT_URL': 'https://test.com/cert',
        'GOOGLE_SUBJECT_EMAIL': 'test@example.com',
        'TIMESHEET_FOLDER_ID': 'test-folder-id',
        'PROJECT_TERMS_FILE_ID': 'test-terms-id',
        'MONTHLY_INVOICING_FOLDER_ID': 'test-invoicing-id',
        'ENVIRONMENT': 'testing',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG'
    }


@pytest.fixture
def mock_env(test_env_vars, monkeypatch):
    """Mock environment variables for testing."""
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Clear the global config to force reload with test values
    import src.config.settings
    src.config.settings._config = None

    yield test_env_vars

    # Clean up
    src.config.settings._config = None


@pytest.fixture
def test_config(mock_env) -> BillingSystemConfig:
    """Test configuration instance."""
    return reload_config()


@pytest.fixture
def mock_google_sheets_service():
    """Mock Google Sheets service."""
    with patch('src.google_auth.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_google_drive_service():
    """Mock Google Drive service."""
    with patch('src.google_auth.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def sample_timesheet_data():
    """Sample timesheet data for testing."""
    return [
        ['Date', 'Project', 'Location', 'Start Time', 'End Time', 'Topics worked on', 'Break', 'Travel time'],
        ['2023-01-02', 'P&C_NEWRETAIL', 'Off-site', '09:30', '17:30', 'Development work', '01:00', '00:00'],
        ['2023-01-03', 'P&C_NEWRETAIL', 'On-site', '08:00', '18:00', 'Client meeting', '01:00', '02:00']
    ]


@pytest.fixture
def sample_project_terms():
    """Sample project terms data for testing."""
    return [
        ['Project', 'Consultant_ID', 'Name', 'Rate', 'Cost', 'Share of travel as work', 'surcharge for travel'],
        ['P&C_NEWRETAIL', 'C001', 'Test Freelancer', '150', '100', '0.5', '0.15']
    ]


@pytest.fixture
def sample_trip_terms():
    """Sample trip terms data for testing."""
    return [
        ['Location', 'Trip Duration', 'Trip Reimbursement'],
        ['Paris On-site', '1', '450'],
        ['Paris On-site', '2', '650']
    ]


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up any test files created during testing."""
    yield

    # Remove test coverage files in case they're created
    test_files = ['coverage.xml', '.coverage']
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)


# Pytest configuration for different test types
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on location."""
    for item in items:
        # Add unit marker for tests in tests/unit/
        if "tests/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker for tests in tests/integration/
        elif "tests/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add api marker for tests that use Google API
        if "api" in item.name.lower() or "google" in item.name.lower():
            item.add_marker(pytest.mark.api)