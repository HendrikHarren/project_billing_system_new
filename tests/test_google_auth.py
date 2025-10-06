"""
Tests for Google API authentication module.
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.google_auth import (
    get_credentials,
    get_drive_service,
    get_sheets_service,
    load_credentials,
)


class TestGoogleAuth:
    """Test cases for Google authentication."""

    @patch("src.google_auth.load_dotenv")
    def test_load_credentials_missing_env_var(self, mock_load_dotenv):
        """Test that missing environment variables raise ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variable"
            ):
                load_credentials()

    @patch("src.google_auth.load_dotenv")
    def test_load_credentials_success(self, mock_load_dotenv):
        """Test successful credentials loading."""
        test_env = {
            "GOOGLE_PROJECT_ID": "test-project",
            "GOOGLE_PRIVATE_KEY_ID": "test-key-id",
            "GOOGLE_PRIVATE_KEY": "test-key",
            "GOOGLE_CLIENT_EMAIL": "test@test.com",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_AUTH_URI": "https://test-auth.com",
            "GOOGLE_TOKEN_URI": "https://test-token.com",
            "GOOGLE_AUTH_PROVIDER_X509_CERT_URL": "https://test-cert.com",
            "GOOGLE_CLIENT_X509_CERT_URL": "https://test-client-cert.com",
        }

        with patch.dict(os.environ, test_env):
            credentials = load_credentials()
            assert credentials["project_id"] == "test-project"
            assert credentials["type"] == "service_account"

    @patch("src.google_auth.service_account.Credentials.from_service_account_info")
    @patch("src.google_auth.load_credentials")
    def test_get_credentials(self, mock_load_credentials, mock_from_service_account):
        """Test get_credentials function without subject parameter."""
        mock_load_credentials.return_value = {"test": "credentials"}
        mock_credentials = Mock()
        mock_from_service_account.return_value = mock_credentials

        result = get_credentials()

        assert result == mock_credentials
        # Verify that credentials are created without subject parameter
        call_args = mock_from_service_account.call_args
        assert call_args[1].get("subject") is None
        mock_from_service_account.assert_called_once()

    @patch("src.google_auth.build")
    @patch("src.google_auth.get_credentials")
    def test_get_sheets_service(self, mock_get_credentials, mock_build):
        """Test get_sheets_service function."""
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_service = Mock()
        mock_build.return_value = mock_service

        result = get_sheets_service()

        mock_build.assert_called_once_with("sheets", "v4", credentials=mock_credentials)
        assert result == mock_service

    @patch("src.google_auth.build")
    @patch("src.google_auth.get_credentials")
    def test_get_drive_service(self, mock_get_credentials, mock_build):
        """Test get_drive_service function."""
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_service = Mock()
        mock_build.return_value = mock_service

        result = get_drive_service()

        mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)
        assert result == mock_service
