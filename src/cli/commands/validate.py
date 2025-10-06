"""Validate data command."""

from datetime import datetime
from typing import List, Optional

import click

from src.cli.utils.formatters import (
    format_error,
    format_info,
    format_success,
    format_warning,
)
from src.config.settings import get_config
from src.readers.timesheet_reader import TimesheetReader
from src.services.google_drive_service import GoogleDriveService
from src.services.google_sheets_service import GoogleSheetsService
from src.validators.validation_report import ValidationIssue, ValidationSeverity
from src.validators.validator import TimesheetValidator


@click.command(name="validate-data")
@click.option(
    "--file-id",
    type=str,
    default=None,
    help="Google Sheets file ID to validate (validates all if not specified)",
)
@click.option(
    "--month",
    type=str,
    default=None,
    help="Validate all timesheets for a specific month (YYYY-MM format)",
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "info"], case_sensitive=False),
    default="error",
    help="Minimum severity level to display (default: error)",
)
def validate_data(file_id: Optional[str], month: Optional[str], severity: str):
    """Validate timesheet data quality.

    Checks for:
    - Field-level validation (dates, times, formats)
    - Business rule compliance
    - Data completeness

    Returns non-zero exit code if errors are found.

    Example:
        billing-cli validate-data --file-id abc123
        billing-cli validate-data --month 2024-10
        billing-cli validate-data --month 2024-10 --severity warning
    """
    try:
        click.echo(format_info("Validating timesheet data..."))

        # Parse severity level
        severity_level = ValidationSeverity[severity.upper()]

        # Initialize services
        settings = get_config()
        credentials = settings.get_google_service_account_info()
        sheets_service = GoogleSheetsService(credentials=credentials)
        drive_service = GoogleDriveService(credentials=credentials)
        reader = TimesheetReader(sheets_service)
        validator = TimesheetValidator()

        # Determine which files to validate
        if file_id:
            click.echo(format_info(f"  Scope: Single file ({file_id})"))
            file_ids = [file_id]
        else:
            # List all files from timesheet folder
            files = drive_service.list_files_in_folder(
                folder_id=settings.timesheet_folder_id,
                mime_type="application/vnd.google-apps.spreadsheet",
            )
            file_ids = [f["id"] for f in files]

            if month:
                click.echo(format_info(f"  Scope: All timesheets for {month}"))
            else:
                click.echo(
                    format_info(f"  Scope: All timesheets ({len(file_ids)} files)")
                )

        # Validate each file
        all_issues: List[ValidationIssue] = []
        files_processed = 0

        click.echo()
        with click.progressbar(file_ids, label="Validating files") as bar:
            for fid in bar:
                try:
                    # Read timesheet entries
                    entries = reader.read_timesheet(fid)

                    # Filter by month if specified
                    if month:
                        month_date = datetime.strptime(month, "%Y-%m")
                        entries = [
                            e
                            for e in entries
                            if e.date.year == month_date.year
                            and e.date.month == month_date.month
                        ]

                    # Validate entries
                    if entries:
                        report = validator.validate_entries(entries)
                        all_issues.extend(report.issues)
                        files_processed += 1

                except Exception as e:
                    # Log error but continue with other files
                    all_issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            field="file",
                            message=f"Failed to read file {fid}: {str(e)}",
                            value=fid,
                        )
                    )

        # Filter issues by severity level
        filtered_issues = [
            i for i in all_issues if i.severity.value >= severity_level.value
        ]

        # Count by severity
        error_count = sum(
            1 for i in all_issues if i.severity == ValidationSeverity.ERROR
        )
        warning_count = sum(
            1 for i in all_issues if i.severity == ValidationSeverity.WARNING
        )
        info_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.INFO)

        # Display results
        click.echo()
        click.echo("=" * 60)
        click.echo("Validation Summary")
        click.echo("=" * 60)
        click.echo(f"Files processed:  {files_processed}")
        click.echo(f"Errors:           {error_count}")
        click.echo(f"Warnings:         {warning_count}")
        click.echo(f"Info:             {info_count}")
        click.echo()

        # Show detailed issues if any match severity filter
        if filtered_issues:
            click.echo(f"Issues (showing {severity.upper()} and above):")
            click.echo("-" * 60)

            # Group by severity
            for sev in [
                ValidationSeverity.ERROR,
                ValidationSeverity.WARNING,
                ValidationSeverity.INFO,
            ]:
                sev_issues = [i for i in filtered_issues if i.severity == sev]
                if sev_issues:
                    click.echo()
                    click.echo(f"{sev.name}S ({len(sev_issues)}):")
                    # Limit to first 20 per severity
                    for issue in sev_issues[:20]:
                        if issue.context:
                            ctx_items = ", ".join(
                                f"{k}={v}" for k, v in issue.context.items()
                            )
                            context_str = f" [{ctx_items}]"
                        else:
                            context_str = ""
                        if sev == ValidationSeverity.ERROR:
                            click.echo(
                                format_error(
                                    f"  {issue.field}: {issue.message}{context_str}"
                                )
                            )
                        elif sev == ValidationSeverity.WARNING:
                            msg_text = f"{issue.field}: {issue.message}{context_str}"
                            click.echo(format_warning(f"  {msg_text}"))
                        else:
                            click.echo(
                                format_info(
                                    f"  {issue.field}: {issue.message}{context_str}"
                                )
                            )

                    if len(sev_issues) > 20:
                        click.echo(f"  ... and {len(sev_issues) - 20} more")

        click.echo()
        click.echo("=" * 60)

        # Return appropriate exit code
        if error_count > 0:
            click.echo()
            click.echo(format_error(f"Validation failed with {error_count} error(s)"))
            raise click.Abort()
        elif warning_count > 0:
            click.echo()
            click.echo(
                format_warning(f"Validation completed with {warning_count} warning(s)")
            )
        else:
            click.echo()
            click.echo(format_success("Validation passed! No issues found."))

    except click.Abort:
        raise
    except Exception as e:
        click.echo()
        click.echo(format_error(f"Failed to validate data: {str(e)}"))
        import traceback

        click.echo(f"\n{traceback.format_exc()}")
        raise click.Abort()
