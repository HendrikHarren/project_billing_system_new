#!/usr/bin/env python3
"""
Demonstration script for Issue #52: Direct Service Account Access

This script demonstrates that the Billing System now works with direct
service account authentication without requiring domain-wide delegation.

Run this script to verify your migration is complete:
    python demo_issue_52.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_config  # noqa: E402
from src.google_auth import (  # noqa: E402
    get_credentials,
    get_drive_service,
    get_sheets_service,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_configuration() -> bool:
    """Test that configuration loads without GOOGLE_SUBJECT_EMAIL."""
    print_section("1. Configuration Test")

    try:
        config = get_config()
        print("✓ Configuration loaded successfully")
        print(f"  - Project ID: {config.google_project_id}")
        print(f"  - Service Account: {config.google_client_email}")

        # Verify GOOGLE_SUBJECT_EMAIL is not present
        if hasattr(config, "google_subject_email"):
            print("✗ ERROR: google_subject_email still exists in configuration!")
            return False
        else:
            print(
                "✓ Confirmed: No domain-wide delegation "
                "(google_subject_email not present)"
            )

        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_authentication() -> bool:
    """Test that authentication works without user impersonation."""
    print_section("2. Authentication Test")

    try:
        credentials = get_credentials()
        print("✓ Credentials created successfully")

        # Verify no subject parameter
        if hasattr(credentials, "subject"):
            print(f"  - Subject: {credentials.subject}")
            if credentials.subject:
                print(
                    "✗ WARNING: Credentials still have a subject (user impersonation)"
                )
                return False

        print(
            "✓ Confirmed: Direct service account authentication (no user impersonation)"
        )
        return True

    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return False


def test_sheets_api() -> bool:
    """Test Google Sheets API connection."""
    print_section("3. Google Sheets API Test")

    try:
        service = get_sheets_service()
        print("✓ Google Sheets service created successfully")

        # Try to access spreadsheet metadata
        config = get_config()
        spreadsheet = (
            service.spreadsheets()
            .get(spreadsheetId=config.project_terms_file_id)
            .execute()
        )

        title = spreadsheet.get("properties", {}).get("title", "Unknown")
        print(f"✓ Successfully accessed project terms file: '{title}'")

        return True

    except Exception as e:
        print(f"✗ Google Sheets API test failed: {e}")
        print("\n  Possible causes:")
        print("  - Service account doesn't have access to project terms file")
        print(
            "  - File not in Shared Drive or not shared directly "
            "with service account"
        )
        print("\n  See docs/MIGRATION_SHARED_DRIVE.md for migration instructions")
        return False


def test_drive_api() -> bool:
    """Test Google Drive API connection."""
    print_section("4. Google Drive API Test")

    try:
        service = get_drive_service()
        print("✓ Google Drive service created successfully")

        # Try to access folder metadata
        config = get_config()
        folder = (
            service.files()
            .get(fileId=config.timesheet_folder_id, fields="id,name")
            .execute()
        )

        name = folder.get("name", "Unknown")
        print(f"✓ Successfully accessed timesheet folder: '{name}'")

        return True

    except Exception as e:
        print(f"✗ Google Drive API test failed: {e}")
        print("\n  Possible causes:")
        print("  - Service account doesn't have access to timesheet folder")
        print(
            "  - Folder not in Shared Drive or not shared directly "
            "with service account"
        )
        print("\n  See docs/MIGRATION_SHARED_DRIVE.md for migration instructions")
        return False


def main() -> int:
    """Run all demonstration tests."""
    print(
        """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         Issue #52 Demonstration: Direct Service Account Access      ║
║                                                                      ║
║  This demo verifies the migration from domain-wide delegation       ║
║  to direct service account authentication is working correctly.     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    )

    tests = [
        ("Configuration", test_configuration),
        ("Authentication", test_authentication),
        ("Google Sheets API", test_sheets_api),
        ("Google Drive API", test_drive_api),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\n✗ Tests interrupted by user")
            return 1
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {e}")
            results.append((test_name, False))

    # Print summary
    print_section("Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print(
            """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  ✓ SUCCESS: All tests passed!                                       ║
║                                                                      ║
║  Your migration to direct service account access is complete.       ║
║  The system is no longer using domain-wide delegation.              ║
║                                                                      ║
║  You can now:                                                        ║
║  1. Generate reports: python -m src.cli generate-report --month ... ║
║  2. (Optional) Remove domain-wide delegation from Admin Console     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
        """
        )
        return 0
    else:
        print(
            """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  ✗ FAILURE: Some tests failed                                       ║
║                                                                      ║
║  Please review the error messages above and:                        ║
║  1. Ensure service account has access to files/folders              ║
║  2. Check that files are in Shared Drive or directly shared         ║
║  3. Verify .env file doesn't have GOOGLE_SUBJECT_EMAIL              ║
║                                                                      ║
║  For detailed migration instructions:                               ║
║  → docs/MIGRATION_SHARED_DRIVE.md                                   ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
        """
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
