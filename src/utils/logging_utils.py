"""Structured logging utilities with context support."""

import functools
import logging
import threading
import uuid
from typing import Any, Callable, Dict, Optional, cast

# Thread-local storage for log context
_thread_local = threading.local()

# Sensitive field names to redact
SENSITIVE_FIELDS = {
    "password",
    "token",
    "api_key",
    "secret",
    "private_key",
    "access_token",
    "refresh_token",
    "credentials",
    "auth",
    "authorization",
}


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for tracking requests.

    Returns:
        UUID string to use as correlation ID
    """
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from thread-local context.

    Returns:
        Current correlation ID or None if not set
    """
    context = getattr(_thread_local, "context", None)
    if context:
        return context.get("correlation_id")
    return None


class LogContext:
    """
    Context manager for adding structured fields to log records.

    This context manager adds custom fields to all log records within its scope.
    Fields are stored in thread-local storage and automatically added to log
    records by the logging system.

    Example:
        with LogContext(freelancer_name="John Doe", project_code="PROJ001"):
            logger.info("Processing timesheet")
            # Log will include freelancer_name and project_code fields
    """

    def __init__(self, **kwargs):
        """
        Initialize log context with custom fields.

        Args:
            **kwargs: Key-value pairs to add to log records
        """
        self.fields = kwargs
        self.previous_context: Optional[Dict[str, Any]] = None

    def __enter__(self):
        """Enter context and add fields to thread-local storage."""
        # Get existing context or create new one
        if not hasattr(_thread_local, "context"):
            _thread_local.context = {}

        # Save previous context for restoration
        self.previous_context = _thread_local.context.copy()

        # Merge new fields with existing context
        _thread_local.context.update(self.fields)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and remove fields from thread-local storage."""
        # Restore previous context
        if self.previous_context is not None:
            _thread_local.context = self.previous_context
        else:
            _thread_local.context = {}


class _ContextFilter(logging.Filter):
    """Logging filter that adds context fields to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context fields to log record.

        Args:
            record: Log record to modify

        Returns:
            True (always allow record through)
        """
        if hasattr(_thread_local, "context"):
            for key, value in _thread_local.context.items():
                setattr(record, key, value)
        return True


def sanitize_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive fields in a dictionary.

    This function recursively processes a dictionary and redacts values
    for fields that match sensitive field names.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary with sensitive values redacted
    """
    if not isinstance(data, dict):
        return data

    sanitized: Dict[str, Any] = {}

    for key, value in data.items():
        # Check if field name is sensitive (case-insensitive)
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = "***REDACTED***" if value is not None else None
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_sensitive_data(cast(Dict[str, Any], value))
        else:
            sanitized[key] = value

    return sanitized


def log_function_call(
    func: Optional[Callable] = None, *, include_args: bool = False, level: str = "DEBUG"
) -> Callable:
    """
    Decorator to log function entry and exit.

    This decorator logs when a function is entered and exited, optionally
    including function arguments. It also logs exceptions if they occur.

    Args:
        func: Function to decorate (when used without arguments)
        include_args: Whether to include function arguments in logs
        level: Log level to use (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Decorated function

    Example:
        @log_function_call
        def process_timesheet(freelancer_name):
            # Function implementation
            pass

        @log_function_call(include_args=True, level="INFO")
        def calculate_billing(hours, rate):
            return hours * rate
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f.__module__)
            log_level = getattr(logging, level.upper())

            # Log function entry
            if include_args:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                logger.log(log_level, f"Entering {f.__name__} with args: {signature}")
            else:
                logger.log(log_level, f"Entering {f.__name__}")

            try:
                # Execute function
                result = f(*args, **kwargs)

                # Log function exit
                logger.log(log_level, f"Exiting {f.__name__}")

                return result

            except Exception as e:
                # Log exception
                logger.error(
                    f"Exception in {f.__name__}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise

        return wrapper

    # Handle both @log_function_call and @log_function_call() syntax
    if func is None:
        # Called with arguments: @log_function_call(include_args=True)
        return decorator
    else:
        # Called without arguments: @log_function_call
        return decorator(func)
