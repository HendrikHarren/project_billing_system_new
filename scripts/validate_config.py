#!/usr/bin/env python
"""
Configuration validation script for Billing System.

Validates all environment variables and tests Google API connectivity.
Exit codes:
    0: All validations passed
    1: Configuration validation failed
    2: Google API connection failed
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import BillingSystemConfig, get_config  # noqa: E402
from src.services import GoogleDriveService, GoogleSheetsService  # noqa: E402


class ConfigValidator:
    """Validates billing system configuration."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.config: BillingSystemConfig | None = None

    def validate_config_loads(self) -> bool:
        """Validate that configuration can be loaded."""
        print("Validating configuration loading...")
        try:
            self.config = get_config()
            print("✓ Configuration loaded successfully")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load configuration: {e}")
            print(f"✗ Configuration loading failed: {e}")
            return False

    def validate_required_fields(self) -> bool:
        """Validate that all required fields are set."""
        if not self.config:
            return False

        print("\nValidating required fields...")
        required_fields = [
            ("google_project_id", "GOOGLE_PROJECT_ID"),
            ("google_private_key", "GOOGLE_PRIVATE_KEY"),
            ("google_client_email", "GOOGLE_CLIENT_EMAIL"),
            ("timesheet_folder_id", "TIMESHEET_FOLDER_ID"),
            ("project_terms_file_id", "PROJECT_TERMS_FILE_ID"),
            ("monthly_invoicing_folder_id", "MONTHLY_INVOICING_FOLDER_ID"),
        ]

        all_valid = True
        for field_name, env_var in required_fields:
            value = getattr(self.config, field_name, None)
            if not value or value == "":
                self.errors.append(f"Required field {env_var} is not set")
                print(f"✗ {env_var} is not set")
                all_valid = False
            else:
                print(f"✓ {env_var} is set")

        return all_valid

    def validate_private_key_format(self) -> bool:
        """Validate private key format."""
        if not self.config:
            return False

        print("\nValidating private key format...")
        key = self.config.google_private_key

        # Check begin marker
        if not key.startswith("-----BEGIN PRIVATE KEY-----"):
            self.errors.append("Private key missing BEGIN marker")
            print("✗ Private key missing BEGIN marker")
            return False

        # Check end marker
        if not key.endswith("-----END PRIVATE KEY-----\n"):
            self.warnings.append("Private key may be missing END marker or newline")
            print("⚠ Private key format may be incorrect (missing END marker)")

        # Check for literal newlines (should have \n, not actual newlines)
        if "\n" in key and key.count("\n") < 3:
            self.warnings.append(
                "Private key appears to have literal \\n instead of newlines"
            )
            print("⚠ Private key may have incorrect newline format")

        print("✓ Private key format appears valid")
        return True

    def validate_email_formats(self) -> bool:
        """Validate email address formats."""
        if not self.config:
            return False

        print("\nValidating email formats...")

        # Client email
        if "@" not in self.config.google_client_email:
            self.errors.append("GOOGLE_CLIENT_EMAIL is not a valid email")
            print("✗ GOOGLE_CLIENT_EMAIL is not valid")
            return False
        print(f"✓ GOOGLE_CLIENT_EMAIL is valid: {self.config.google_client_email}")

        # Subject email
        if "@" not in self.config.google_subject_email:
            self.warnings.append("GOOGLE_SUBJECT_EMAIL may not be valid")
            print(
                f"⚠ GOOGLE_SUBJECT_EMAIL may not be valid: "
                f"{self.config.google_subject_email}"
            )
        else:
            print(
                f"✓ GOOGLE_SUBJECT_EMAIL is valid: "
                f"{self.config.google_subject_email}"
            )

        return True

    def validate_environment_settings(self) -> bool:
        """Validate environment-specific settings."""
        if not self.config:
            return False

        print("\nValidating environment settings...")

        # Environment
        valid_envs = ["development", "testing", "production"]
        if self.config.environment not in valid_envs:
            self.errors.append(
                f"Invalid environment: {self.config.environment}. "
                f"Must be one of: {valid_envs}"
            )
            print(f"✗ Invalid environment: {self.config.environment}")
            return False
        print(f"✓ Environment: {self.config.environment}")

        # Log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.log_level not in valid_levels:
            self.errors.append(
                f"Invalid log level: {self.config.log_level}. "
                f"Must be one of: {valid_levels}"
            )
            print(f"✗ Invalid log level: {self.config.log_level}")
            return False
        print(f"✓ Log level: {self.config.log_level}")

        # Cache settings
        print(f"✓ Cache enabled: {self.config.enable_sheets_cache}")
        print(f"✓ Cache file: {self.config.cache_file_path}")
        print(f"✓ Cache max size: {self.config.cache_max_size}")

        return True

    def test_google_api_connection(self) -> bool:
        """Test Google API connectivity."""
        if not self.config:
            return False

        print("\nTesting Google API connections...")

        try:
            # Get service account credentials
            credentials = self.config.get_google_service_account_info()
            subject_email = self.config.google_subject_email

            # Test Sheets API
            GoogleSheetsService(credentials=credentials, subject_email=subject_email)
            print("✓ Google Sheets API connection successful")

            # Test Drive API
            GoogleDriveService(credentials=credentials, subject_email=subject_email)
            print("✓ Google Drive API connection successful")

            return True

        except Exception as e:
            self.errors.append(f"Google API connection failed: {e}")
            print(f"✗ Google API connection failed: {e}")
            return False

    def test_file_access(self) -> bool:
        """Test access to required Google Drive files and folders."""
        if not self.config:
            return False

        print("\nTesting file access...")

        try:
            # Get service account credentials
            credentials = self.config.get_google_service_account_info()
            subject_email = self.config.google_subject_email

            # Create service instances
            drive_service = GoogleDriveService(
                credentials=credentials, subject_email=subject_email
            )
            sheets_service = GoogleSheetsService(
                credentials=credentials, subject_email=subject_email
            )

            # Test timesheet folder access
            folder = drive_service.get_file_metadata(self.config.timesheet_folder_id)
            print(f"✓ Timesheet folder accessible: {folder.get('name', 'Unknown')}")

            # Test project terms file access
            spreadsheet = sheets_service.get_spreadsheet_metadata(
                self.config.project_terms_file_id
            )
            print(
                f"✓ Project terms file accessible: "
                f"{spreadsheet.get('properties', {}).get('title', 'Unknown')}"
            )

            # Test output folder access
            output_folder = drive_service.get_file_metadata(
                self.config.monthly_invoicing_folder_id
            )
            print(f"✓ Output folder accessible: {output_folder.get('name', 'Unknown')}")

            return True

        except Exception as e:
            self.errors.append(f"File access test failed: {e}")
            print(f"✗ File access test failed: {e}")
            return False

    def run_all_validations(self) -> Tuple[bool, int, int]:
        """
        Run all validation checks.

        Returns:
            Tuple of (success, error_count, warning_count)
        """
        print("=" * 60)
        print("Billing System Configuration Validation")
        print("=" * 60)

        # Run validations
        validations = [
            self.validate_config_loads(),
            self.validate_required_fields(),
            self.validate_private_key_format(),
            self.validate_email_formats(),
            self.validate_environment_settings(),
            self.test_google_api_connection(),
            self.test_file_access(),
        ]

        all_passed = all(validations)

        # Print summary
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)

        if all_passed and not self.errors:
            print("✓ All validation checks passed!")
        else:
            print(f"✗ Validation failed with {len(self.errors)} error(s)")

        if self.warnings:
            print(f"⚠ {len(self.warnings)} warning(s) found")

        # Print errors
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  ✗ {error}")

        # Print warnings
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        return all_passed, len(self.errors), len(self.warnings)


def main() -> int:
    """Main entry point."""
    validator = ConfigValidator()
    success, error_count, warning_count = validator.run_all_validations()

    if not success or error_count > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
