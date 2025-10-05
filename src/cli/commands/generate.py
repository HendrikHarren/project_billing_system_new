"""Generate report command."""

import time
from datetime import datetime
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


@click.command(name="generate-report")
@click.option(
    "--month",
    required=True,
    type=str,
    help="Month to generate report for (YYYY-MM format)",
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
    month: str,
    project: Optional[str],
    freelancer: Optional[str],
    output_folder: Optional[str],
):
    """Generate billing report for specified month.

    This command orchestrates the full pipeline:
    1. Read timesheets from Google Drive
    2. Load project terms
    3. Aggregate and calculate billing
    4. Generate master timesheet
    5. Write to Google Sheets

    Example:
        billing-cli generate-report --month 2024-10
        billing-cli generate-report --month 2024-10 --project PROJ001
    """
    start_time = time.time()

    try:
        # Validate month format
        try:
            month_date = datetime.strptime(month, "%Y-%m")
            year = month_date.year
            month_num = month_date.month
        except ValueError:
            click.echo(format_error(f"Invalid month format: {month}. Expected YYYY-MM"))
            raise click.Abort()

        click.echo(format_info(f"Generating report for {month}..."))
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
        sheets_service = GoogleSheetsService()
        drive_service = GoogleDriveService()
        timesheet_reader = TimesheetReader(sheets_service)
        project_terms_reader = ProjectTermsReader(
            sheets_service, settings.project_terms_file_id
        )
        tracker.advance()

        # Stage 2: Aggregate data
        click.echo(tracker.get_current_message())
        aggregator = TimesheetAggregator(
            timesheet_reader, project_terms_reader, drive_service
        )

        aggregated_data = aggregator.aggregate_timesheets(settings.timesheet_folder_id)
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
        writer = GoogleSheetsWriter(sheets_service, drive_service)
        folder_id = output_folder or settings.monthly_invoicing_folder_id

        file_id, url = writer.write_master_timesheet(
            master_data=master_data,
            output_folder_id=folder_id,
            filename_prefix=f"Billing_Report_{month}",
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
