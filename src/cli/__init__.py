"""Billing System CLI.

This module provides a command-line interface for the billing system.
It includes commands for generating reports, listing timesheets, and validating data.
"""

import click

from src.cli.commands.generate import generate_report
from src.cli.commands.list import list_timesheets
from src.cli.commands.validate import validate_data

__version__ = "1.0.0"


@click.group(
    help="Billing System CLI - Process freelancer timesheets and generate reports"
)
@click.version_option(version=__version__)
def cli():
    """Billing System CLI main entry point."""
    pass


# Register commands
cli.add_command(generate_report)
cli.add_command(list_timesheets)
cli.add_command(validate_data)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
