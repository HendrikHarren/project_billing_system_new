"""Enhanced error handling for CLI commands."""

import sys
import traceback
from typing import Optional

import click
from googleapiclient.errors import HttpError

from src.cli.utils.formatters import format_error, format_warning


class CLIError(Exception):
    """Base exception for CLI errors with user-friendly messages."""

    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        """
        Initialize CLI error.

        Args:
            message: Error message to display
            recovery_hint: Optional hint for recovering from the error
        """
        self.message = message
        self.recovery_hint = recovery_hint
        super().__init__(message)


class ConfigurationError(CLIError):
    """Error related to configuration issues."""

    pass


class APIError(CLIError):
    """Error related to Google API calls."""

    pass


class DataValidationError(CLIError):
    """Error related to data validation."""

    pass


class ProcessingError(CLIError):
    """Error related to data processing."""

    pass


def handle_cli_error(error: Exception, debug: bool = False) -> int:
    """
    Handle CLI errors with user-friendly messages.

    Args:
        error: The exception that occurred
        debug: Whether to show full stack trace

    Returns:
        Exit code (1-9 for different error types)
    """
    # Handle our custom CLI errors
    if isinstance(error, ConfigurationError):
        click.echo(format_error(f"Configuration Error: {error.message}"))
        if error.recovery_hint:
            click.echo(format_warning(f"Hint: {error.recovery_hint}"))
        return 1

    elif isinstance(error, APIError):
        click.echo(format_error(f"API Error: {error.message}"))
        if error.recovery_hint:
            click.echo(format_warning(f"Hint: {error.recovery_hint}"))
        return 2

    elif isinstance(error, DataValidationError):
        click.echo(format_error(f"Data Validation Error: {error.message}"))
        if error.recovery_hint:
            click.echo(format_warning(f"Hint: {error.recovery_hint}"))
        return 3

    elif isinstance(error, ProcessingError):
        click.echo(format_error(f"Processing Error: {error.message}"))
        if error.recovery_hint:
            click.echo(format_warning(f"Hint: {error.recovery_hint}"))
        return 4

    # Handle Google API HTTP errors
    elif isinstance(error, HttpError):
        status_code = error.resp.status

        if status_code == 401:
            click.echo(format_error("Authentication Failed"))
            click.echo(
                format_warning(
                    "Hint: Check your service account credentials in the .env file"
                )
            )
            return 5

        elif status_code == 403:
            click.echo(format_error("Permission Denied"))
            click.echo(
                format_warning(
                    "Hint: Ensure your service account has access to "
                    "the requested resources"
                )
            )
            return 6

        elif status_code == 404:
            click.echo(format_error("Resource Not Found"))
            click.echo(
                format_warning("Hint: Verify the file/folder ID in your configuration")
            )
            return 7

        elif status_code == 429:
            click.echo(format_error("Rate Limit Exceeded"))
            click.echo(
                format_warning(
                    "Hint: Wait a few minutes before retrying, or reduce "
                    "concurrent requests"
                )
            )
            return 8

        else:
            click.echo(format_error(f"Google API Error (HTTP {status_code})"))
            click.echo(format_warning(f"Details: {str(error)}"))
            return 9

    # Handle click.Abort (user cancellation)
    elif isinstance(error, click.Abort):
        click.echo(format_warning("\nOperation cancelled by user"))
        return 130  # Standard exit code for SIGINT

    # Handle generic exceptions
    else:
        click.echo(format_error(f"Unexpected Error: {type(error).__name__}"))
        click.echo(str(error))

        if debug:
            click.echo("\nFull stack trace:")
            click.echo(traceback.format_exc())
        else:
            click.echo(format_warning("\nRun with --debug flag for full stack trace"))

        return 255


def with_error_handling(debug: bool = False):
    """
    Decorator to add standardized error handling to CLI commands.

    Args:
        debug: Whether to show full stack traces

    Returns:
        Decorator function

    Example:
        @click.command()
        @click.option('--debug', is_flag=True)
        def my_command(debug):
            with with_error_handling(debug):
                # Command implementation
                pass
    """

    class ErrorHandler:
        """Context manager for error handling."""

        def __init__(self, show_debug: bool):
            self.show_debug = show_debug

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_val is not None:
                exit_code = handle_cli_error(exc_val, self.show_debug)
                sys.exit(exit_code)
            return False  # Don't suppress exceptions

    return ErrorHandler(debug)
