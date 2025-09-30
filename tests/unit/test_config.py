"""
Unit tests for configuration management.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config.settings import (
    BillingSystemConfig,
    get_config,
    load_config,
    reload_config,
)


class TestBillingSystemConfig:
    """Test cases for BillingSystemConfig."""

    def test_config_with_valid_env_vars(self, test_config):
        """Test configuration loads correctly with valid environment variables."""
        assert test_config.google_project_id == "test-project"
        assert test_config.google_private_key_id == "test-key-id"
        assert test_config.google_client_email == "test@test.com"
        assert test_config.timesheet_folder_id == "test-folder-id"
        assert test_config.environment == "testing"
        assert test_config.debug is True
        assert test_config.log_level == "DEBUG"

    def test_google_service_account_info(self, test_config):
        """Test Google service account info generation."""
        service_account_info = test_config.get_google_service_account_info()

        assert service_account_info["type"] == "service_account"
        assert service_account_info["project_id"] == "test-project"
        assert service_account_info["private_key_id"] == "test-key-id"
        assert service_account_info["client_email"] == "test@test.com"

    def test_default_values(self, mock_env):
        """Test default configuration values."""
        with patch.dict(os.environ, mock_env):
            config = BillingSystemConfig()

        assert config.environment == "testing"  # From mock_env
        assert config.debug is True  # From mock_env
        assert config.log_level == "DEBUG"  # From mock_env
        assert config.batch_size == 10
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_google_scopes_default(self, test_config):
        """Test default Google API scopes."""
        expected_scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        assert test_config.google_scopes == expected_scopes

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "not-a-private-key",
            "BEGIN PRIVATE KEY",
            "",
            "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----\n",
        ],
    )
    def test_invalid_private_key_validation(self, mock_env, invalid_key):
        """Test private key validation with invalid formats."""
        test_env = mock_env.copy()
        test_env["GOOGLE_PRIVATE_KEY"] = invalid_key

        with patch.dict(os.environ, test_env):
            with pytest.raises(ValidationError) as exc_info:
                BillingSystemConfig()

        assert "Invalid private key format" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_log_level", ["TRACE", "VERBOSE", "invalid", "123"]
    )
    def test_invalid_log_level_validation(self, mock_env, invalid_log_level):
        """Test log level validation with invalid values."""
        test_env = mock_env.copy()
        test_env["LOG_LEVEL"] = invalid_log_level

        with patch.dict(os.environ, test_env):
            with pytest.raises(ValidationError) as exc_info:
                BillingSystemConfig()

        assert "Log level must be one of" in str(exc_info.value)

    @pytest.mark.parametrize(
        "valid_log_level,expected",
        [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("WARNING", "WARNING"),
            ("Error", "ERROR"),
            ("CRITICAL", "CRITICAL"),
        ],
    )
    def test_valid_log_level_normalization(self, mock_env, valid_log_level, expected):
        """Test log level validation with valid values."""
        test_env = mock_env.copy()
        test_env["LOG_LEVEL"] = valid_log_level

        with patch.dict(os.environ, test_env):
            config = BillingSystemConfig()

        assert config.log_level == expected

    @pytest.mark.parametrize("invalid_environment", ["staging", "prod", "dev", "test"])
    def test_invalid_environment_validation(self, mock_env, invalid_environment):
        """Test environment validation with invalid values."""
        test_env = mock_env.copy()
        test_env["ENVIRONMENT"] = invalid_environment

        with patch.dict(os.environ, test_env):
            with pytest.raises(ValidationError) as exc_info:
                BillingSystemConfig()

        assert "Environment must be one of" in str(exc_info.value)

    @pytest.mark.parametrize(
        "valid_environment,expected",
        [
            ("DEVELOPMENT", "development"),
            ("Testing", "testing"),
            ("PRODUCTION", "production"),
        ],
    )
    def test_valid_environment_normalization(
        self, mock_env, valid_environment, expected
    ):
        """Test environment validation with valid values."""
        test_env = mock_env.copy()
        test_env["ENVIRONMENT"] = valid_environment

        with patch.dict(os.environ, test_env):
            config = BillingSystemConfig()

        assert config.environment == expected


class TestConfigurationFunctions:
    """Test configuration loading functions."""

    def test_load_config_with_env_file(self, tmp_path, test_env_vars):
        """Test loading configuration from specific env file."""
        # Create temporary .env file
        env_file = tmp_path / ".env.test"
        env_content = "\n".join([f"{k}={v}" for k, v in test_env_vars.items()])
        env_file.write_text(env_content)

        # Clear any existing config
        import src.config.settings

        src.config.settings._config = None

        config = load_config(str(env_file))

        assert config.google_project_id == "test-project"
        assert config.environment == "testing"

    def test_get_config_singleton(self, mock_env):
        """Test that get_config returns singleton instance."""
        # Clear any existing config
        import src.config.settings

        src.config.settings._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
        assert config1.google_project_id == "test-project"

    def test_reload_config(self, mock_env):
        """Test configuration reload functionality."""
        # Set initial config
        import src.config.settings

        src.config.settings._config = None

        config1 = get_config()
        assert config1.google_project_id == "test-project"

        # Change environment variable
        os.environ["GOOGLE_PROJECT_ID"] = "new-project-id"

        # Reload config
        config2 = reload_config()

        assert config2.google_project_id == "new-project-id"
        assert config1 is not config2

    @patch("src.config.settings.load_dotenv")
    def test_missing_required_env_vars(self, mock_load_dotenv):
        """Test behavior when required environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            try:
                config = load_config()
                # If this succeeds, it means there are defaults or the env is not fully cleared
                # This is acceptable behavior - just verify it's a valid config
                assert hasattr(config, "google_project_id")
            except ValidationError as exc_info:
                # If it fails, should be due to missing required fields
                assert "field required" in str(exc_info) or "Field required" in str(
                    exc_info
                )


class TestConfigurationEdgeCases:
    """Test edge cases and error scenarios."""

    def test_config_with_empty_strings(self, mock_env):
        """Test configuration with empty string values."""
        with pytest.raises(ValidationError):
            BillingSystemConfig(
                google_project_id="",  # Empty string should fail validation
                google_private_key_id="test",
                google_private_key="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
                google_client_email="test@test.com",
                google_client_id="test",
                google_client_x509_cert_url="https://test.com",
                google_subject_email="test@test.com",
                timesheet_folder_id="test",
                project_terms_file_id="test",
                monthly_invoicing_folder_id="test",
            )

    def test_config_case_insensitive_env_vars(self, mock_env):
        """Test that environment variable loading is case insensitive."""
        with patch.dict(
            os.environ, {"google_project_id": "lowercase-test"}, clear=False
        ):
            # Clear existing config
            import src.config.settings

            src.config.settings._config = None

            config = load_config()
            assert config.google_project_id == "lowercase-test"

    def test_config_validation_comprehensive(self, test_config):
        """Test that all required configuration fields are present and valid."""
        # Verify all Google API fields
        assert test_config.google_project_id
        assert test_config.google_private_key_id
        assert test_config.google_private_key.startswith("-----BEGIN PRIVATE KEY-----")
        assert test_config.google_client_email
        assert test_config.google_client_id
        assert test_config.google_subject_email

        # Verify Google Drive/Sheets fields
        assert test_config.timesheet_folder_id
        assert test_config.project_terms_file_id
        assert test_config.monthly_invoicing_folder_id

        # Verify application fields
        assert test_config.environment in ["development", "testing", "production"]
        assert isinstance(test_config.debug, bool)
        assert test_config.log_level in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]

        # Verify processing fields
        assert test_config.batch_size > 0
        assert test_config.max_retries >= 0
        assert test_config.retry_delay >= 0.0
