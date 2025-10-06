"""List timesheets command."""

import re
from datetime import datetime
from typing import Optional

import click

from src.cli.utils.formatters import (
    format_error,
    format_info,
    format_success,
    format_table,
)
from src.config.settings import get_config
from src.services.google_drive_service import GoogleDriveService


@click.command(name="list-timesheets")
@click.option(
    "--folder-id",
    type=str,
    default=None,
    help="Google Drive folder ID (optional, uses default from config)",
)
def list_timesheets(folder_id: Optional[str]):
    """List available timesheets from Google Drive.

    Displays a table with:
    - Freelancer name
    - File ID
    - Last modified date

    Example:
        billing-cli list-timesheets
        billing-cli list-timesheets --folder-id abc123xyz
    """
    try:
        click.echo(format_info("Fetching timesheets from Google Drive..."))

        # Initialize services with credentials from config
        settings = get_config()
        credentials = settings.get_google_service_account_info()
        drive_service = GoogleDriveService(credentials=credentials)

        # Get folder ID from config if not provided
        target_folder_id = folder_id or settings.timesheet_folder_id

        # List files from Google Drive
        files = drive_service.list_files_in_folder(
            folder_id=target_folder_id,
            mime_type="application/vnd.google-apps.spreadsheet",
        )

        if not files:
            click.echo()
            click.echo(format_info("No timesheets found in the specified folder."))
            return

        # Extract freelancer names from file names
        headers = ["Freelancer", "File ID", "Last Modified"]
        rows = []

        for file_info in files:
            name = file_info.get("name", "Unknown")
            file_id = file_info.get("id", "")
            modified_time = file_info.get("modifiedTime", "")

            # Extract freelancer name
            freelancer_name = _extract_freelancer_name(name)

            # Format modified time
            if modified_time:
                try:
                    dt = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
                    modified_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    modified_display = modified_time[:10]  # Just show date part
            else:
                modified_display = "N/A"

            rows.append([freelancer_name, file_id[:15] + "...", modified_display])

        # Display table
        click.echo()
        click.echo(format_table(headers, rows))
        click.echo()
        click.echo(format_success(f"Found {len(files)} timesheet(s)"))

    except Exception as e:
        click.echo()
        click.echo(format_error(f"Failed to list timesheets: {str(e)}"))
        import traceback

        click.echo(f"\n{traceback.format_exc()}")
        raise click.Abort()


def _extract_freelancer_name(filename: str) -> str:
    """Extract freelancer name from filename.

    Args:
        filename: The file name to parse

    Returns:
        Extracted freelancer name or the original filename
    """
    # Remove file extension
    name = filename.replace(".xlsx", "").replace(".xls", "")

    # Common patterns to remove
    patterns_to_remove = [
        r"^Timesheet_",
        r"^timesheet_",
        r"^Zeiterfassung_",
        r"^zeiterfassung_",
    ]

    for pattern in patterns_to_remove:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # Replace underscores with spaces
    name = name.replace("_", " ")

    # Capitalize words
    name = " ".join(word.capitalize() for word in name.split())

    return name if name else filename
