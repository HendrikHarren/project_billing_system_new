"""Generate report command."""

import datetime as dt
import time
from calendar import monthrange
from typing import Optional

import click

from src.aggregators.timesheet_aggregator import TimesheetAggregator
from src.cli.utils.formatters import format_error, format_info, format_success
from src.cli.utils.progress import ProgressTracker
from src.config.settings import get_config
from src.readers.project_terms_reader import ProjectTermsReader
from src.readers.timesheet_reader import TimesheetReader
from src.services.google_drive_service import GoogleDriveService
from src.services.google_sheets_service import GoogleSheetsService
from src.writers.google_sheets_writer import GoogleSheetsWriter
from src.writers.master_timesheet_generator import MasterTimesheetGenerator


def parse_date_input(date_str: str) -> dt.date:
    """Parse date string in YYYY-MM or YYYY-MM-DD format.

    Args:
        date_str: Date string in YYYY-MM or YYYY-MM-DD format

    Returns:
        Parsed date object

    Raises:
        ValueError: If date format is invalid
    """
    # Try YYYY-MM-DD format first
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try YYYY-MM format (use first day of month)
    try:
        parsed = dt.datetime.strptime(date_str, "%Y-%m")
        return dt.date(parsed.year, parsed.month, 1)
    except ValueError:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected YYYY-MM-DD or YYYY-MM"
        )


@click.command(name="generate-report")
@click.option(
    "--month",
    required=False,
    type=str,
    default=None,
    help=(
        "Month to generate report for (YYYY-MM format). "
        "Cannot be used with --date-range or --start-date/--end-date."
    ),
)
@click.option(
    "--date-range",
    required=False,
    type=str,
    nargs=2,
    default=None,
    help=(
        "Custom date range as START END (YYYY-MM format). "
        "Example: --date-range 2023-01 2024-12. "
        "Cannot be used with --month or --start-date/--end-date."
    ),
)
@click.option(
    "--start-date",
    required=False,
    type=str,
    default=None,
    help=(
        "Start date (YYYY-MM-DD or YYYY-MM format). "
        "Must be used with --end-date. "
        "Cannot be used with --month or --date-range."
    ),
)
@click.option(
    "--end-date",
    required=False,
    type=str,
    default=None,
    help=(
        "End date (YYYY-MM-DD or YYYY-MM format). "
        "Must be used with --start-date. "
        "Cannot be used with --month or --date-range."
    ),
)
@click.option(
    "--project",
    type=str,
    default=None,
    help="Filter by project code (optional)",
)
@click.option(
    "--freelancer",
    type=str,
    default=None,
    help="Filter by freelancer name (optional)",
)
@click.option(
    "--output-folder",
    type=str,
    default=None,
    help="Google Drive folder ID for output (optional, uses default from config)",
)
def generate_report(
    month: Optional[str],
    date_range: Optional[tuple],
    start_date: Optional[str],
    end_date: Optional[str],
    project: Optional[str],
    freelancer: Optional[str],
    output_folder: Optional[str],
):
    """Generate billing report for specified month or date range.

    This command orchestrates the full pipeline:
    1. Read timesheets from Google Drive
    2. Filter entries by date range (from parameters or defaults)
    3. Apply optional project and freelancer filters
    4. Calculate billing for filtered entries only (performance optimization)
    5. Generate master timesheet
    6. Write to Google Sheets with pivot table filters

    Date Options (mutually exclusive):
    - --month: Single month (YYYY-MM)
    - --date-range: Custom range (START END in YYYY-MM format)
    - --start-date/--end-date: Custom range (YYYY-MM-DD or YYYY-MM)
    - No date options: Default to current + previous year

    Example:
        billing-cli generate-report --month 2024-10
        billing-cli generate-report --date-range 2023-01 2024-12
        billing-cli generate-report --start-date 2024-01-01 --end-date 2024-06-30
        billing-cli generate-report  # Uses default (2024-2025)
    """
    start_time = time.time()

    try:
        # Validate that only one date option is used
        date_options_count = sum(
            [
                month is not None,
                date_range is not None,
                start_date is not None or end_date is not None,
            ]
        )

        if date_options_count > 1:
            click.echo(
                format_error(
                    "Cannot use multiple date options. Choose ONE of: "
                    "--month, --date-range, or --start-date/--end-date"
                )
            )
            raise click.Abort()

        # Validate that start_date and end_date are used together
        if (start_date is not None) != (end_date is not None):
            click.echo(
                format_error("--start-date and --end-date must be used together")
            )
            raise click.Abort()

        # Handle month parameter
        if month is not None:
            # Validate month format and calculate date range
            try:
                month_date = dt.datetime.strptime(month, "%Y-%m")
                year = month_date.year
                month_num = month_date.month

                # Calculate first and last day of the month
                start_date_parsed = dt.date(year, month_num, 1)
                _, last_day = monthrange(year, month_num)
                end_date_parsed = dt.date(year, month_num, last_day)
                filename_prefix = f"Billing_Report_{month}"
            except ValueError:
                click.echo(
                    format_error(f"Invalid month format: {month}. Expected YYYY-MM")
                )
                raise click.Abort()

            click.echo(format_info(f"Generating report for {month}..."))
            click.echo(
                format_info(f"  Date range: {start_date_parsed} to {end_date_parsed}")
            )

        # Handle date-range parameter
        elif date_range is not None:
            try:
                # date_range is a tuple of (start, end) in YYYY-MM format
                start_str, end_str = date_range

                # Parse start date (first day of month)
                start_parsed = dt.datetime.strptime(start_str, "%Y-%m")
                start_date_parsed = dt.date(start_parsed.year, start_parsed.month, 1)

                # Parse end date (last day of month)
                end_parsed = dt.datetime.strptime(end_str, "%Y-%m")
                _, last_day = monthrange(end_parsed.year, end_parsed.month)
                end_date_parsed = dt.date(end_parsed.year, end_parsed.month, last_day)

                year = None
                month_num = None
                filename_prefix = f"Billing_Report_{start_str}_to_{end_str}"
            except ValueError as e:
                error_msg = (
                    f"Invalid date-range format. "
                    f"Expected YYYY-MM YYYY-MM. Error: {e}"
                )
                click.echo(format_error(error_msg))
                raise click.Abort()

            click.echo(format_info("Generating report for date range..."))
            click.echo(
                format_info(f"  Date range: {start_date_parsed} to {end_date_parsed}")
            )

        # Handle start-date and end-date parameters
        elif start_date is not None and end_date is not None:
            try:
                start_date_parsed = parse_date_input(start_date)
                end_date_parsed = parse_date_input(end_date)

                if start_date_parsed > end_date_parsed:
                    click.echo(
                        format_error("start-date must be before or equal to end-date")
                    )
                    raise click.Abort()

                year = None
                month_num = None
                filename_prefix = (
                    f"Billing_Report_{start_date_parsed.isoformat()}_to_"
                    f"{end_date_parsed.isoformat()}"
                )
            except ValueError as e:
                click.echo(format_error(str(e)))
                raise click.Abort()

            click.echo(format_info("Generating report for custom date range..."))
            click.echo(
                format_info(f"  Date range: {start_date_parsed} to {end_date_parsed}")
            )

        # No date parameters - use defaults
        else:
            # Use defaults (current + previous year)
            start_date_parsed = None
            end_date_parsed = None
            year = None
            month_num = None
            today = dt.date.today()
            current_year = today.year
            filename_prefix = f"Billing_Report_{current_year - 1}-{current_year}"

            click.echo(format_info("Generating report with default date range..."))
            date_range_text = (
                f"  Date range: {current_year - 1}-01-01 to "
                f"{current_year}-12-31 (default)"
            )
            click.echo(format_info(date_range_text))

        if project:
            click.echo(format_info(f"  Filter: Project = {project}"))
        if freelancer:
            click.echo(format_info(f"  Filter: Freelancer = {freelancer}"))
        click.echo()

        stages = [
            "Reading timesheets from Google Drive",
            "Aggregating and calculating billing",
            "Generating master timesheet",
            "Writing to Google Sheets",
            "Complete",
        ]
        tracker = ProgressTracker(stages)

        # Stage 1: Initialize services
        click.echo(tracker.get_current_message())
        settings = get_config()
        credentials = settings.get_google_service_account_info()
        sheets_service = GoogleSheetsService(
            credentials=credentials, subject_email=settings.google_subject_email
        )
        drive_service = GoogleDriveService(
            credentials=credentials, subject_email=settings.google_subject_email
        )
        timesheet_reader = TimesheetReader(sheets_service)
        project_terms_reader = ProjectTermsReader(
            sheets_service, settings.project_terms_file_id
        )
        tracker.advance()

        # Stage 2: Aggregate data with filters
        click.echo(tracker.get_current_message())
        aggregator = TimesheetAggregator(
            timesheet_reader, project_terms_reader, drive_service
        )

        aggregated_data = aggregator.aggregate_timesheets(
            settings.timesheet_folder_id,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            project_code=project,
            freelancer_name=freelancer,
        )
        tracker.advance(f"Processed {len(aggregated_data.entries)} entries")

        # Stage 3: Generate master timesheet
        click.echo(tracker.get_current_message())
        generator = MasterTimesheetGenerator(aggregated_data)
        master_data = generator.generate()
        tracker.advance(
            f"Generated {len(master_data.timesheet_master)} rows, "
            f"{len(master_data.trips_master)} trips"
        )

        # Stage 4: Write to Google Sheets
        click.echo(tracker.get_current_message())
        writer = GoogleSheetsWriter(sheets_service._service, drive_service._service)
        folder_id = output_folder or settings.monthly_invoicing_folder_id

        file_id, url = writer.write_master_timesheet(
            master_data=master_data,
            output_folder_id=folder_id,
            filename_prefix=filename_prefix,
            project_filter=project,
            year_filter=year,
            month_filter=month_num,
        )
        tracker.advance(f"File created: {file_id}")

        # Stage 5: Complete
        click.echo(tracker.get_current_message())

        # Show summary
        duration = time.time() - start_time
        click.echo()
        click.echo(format_success("Report generated successfully!"))
        click.echo()
        click.echo("Summary:")
        click.echo(f"  Entries processed: {len(aggregated_data.entries)}")
        click.echo(f"  Trips identified:  {len(master_data.trips_master)}")
        click.echo(f"  File ID:          {file_id}")
        click.echo(f"  URL:              {url}")
        click.echo(f"  Duration:         {duration:.2f}s")

    except click.Abort:
        raise
    except Exception as e:
        click.echo()
        click.echo(format_error(f"Failed to generate report: {str(e)}"))
        import traceback

        click.echo(f"\n{traceback.format_exc()}")
        raise click.Abort()
