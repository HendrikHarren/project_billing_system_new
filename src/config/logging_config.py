"""Centralized logging configuration for the billing system."""

import json
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation of log record
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record.__dict__
        # These are fields added via extra={} in logging calls
        skip_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
        }

        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data)


class LoggingConfig:
    """
    Configuration for centralized logging.

    Attributes:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('standard' or 'json')
        log_file: Path to log file (optional)
        enable_console: Enable console output
        enable_file: Enable file output
        max_file_size: Maximum log file size in bytes (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """

    VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    VALID_FORMATS = {"standard", "json"}

    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "standard",
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_file: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        """
        Initialize logging configuration.

        Args:
            log_level: Logging level
            log_format: Format type ('standard' or 'json')
            log_file: Path to log file
            enable_console: Enable console logging
            enable_file: Enable file logging
            max_file_size: Maximum log file size in bytes
            backup_count: Number of rotating backup files

        Raises:
            ValueError: If invalid log level or format
        """
        if log_level.upper() not in self.VALID_LEVELS:
            raise ValueError(
                f"Invalid log level: {log_level}. "
                f"Must be one of {', '.join(self.VALID_LEVELS)}"
            )

        if log_format not in self.VALID_FORMATS:
            raise ValueError(
                f"Invalid log format: {log_format}. "
                f"Must be one of {', '.join(self.VALID_FORMATS)}"
            )

        if enable_file and not log_file:
            raise ValueError("log_file must be specified when enable_file is True")

        self.log_level = log_level.upper()
        self.log_format = log_format
        self.log_file = log_file
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """
        Create configuration from environment variables.

        Environment Variables:
            LOG_LEVEL: Log level (default: INFO)
            LOG_FORMAT: Log format (default: standard)
            LOG_FILE: Log file path (default: None)
            LOG_CONSOLE: Enable console output (default: true)
            LOG_FILE_ENABLED: Enable file output (default: false)
            LOG_MAX_FILE_SIZE: Max file size in bytes (default: 10485760)
            LOG_BACKUP_COUNT: Backup file count (default: 5)

        Returns:
            LoggingConfig instance
        """
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "standard"),
            log_file=os.getenv("LOG_FILE"),
            enable_console=os.getenv("LOG_CONSOLE", "true").lower() == "true",
            enable_file=os.getenv("LOG_FILE_ENABLED", "false").lower() == "true",
            max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )


def configure_logging(config: LoggingConfig) -> None:
    """
    Configure logging for the application.

    This function sets up logging handlers, formatters, and levels
    according to the provided configuration.

    Args:
        config: LoggingConfig instance
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # Set root logger level
    root_logger.setLevel(getattr(logging, config.log_level))

    # Create formatter based on config
    if config.log_format == "json":
        formatter = JSONFormatter()
    else:
        # Standard format with timestamp, level, logger name, and message
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Create context filter for structured logging
    from src.utils.logging_utils import _ContextFilter

    context_filter = _ContextFilter()

    # Add console handler if enabled
    if config.enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.log_level))
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        root_logger.addHandler(console_handler)

    # Add file handler if enabled
    if config.enable_file and config.log_file:
        # Create log directory if it doesn't exist
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to prevent unlimited growth
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
        )
        file_handler.setLevel(getattr(logging, config.log_level))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    This is a convenience function that returns a standard Python logger.
    All loggers will use the configuration set by configure_logging().

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def reset_logging() -> None:
    """
    Reset logging configuration to defaults.

    This function removes all handlers and resets the root logger level.
    Useful for testing and cleanup.
    """
    root_logger = logging.getLogger()

    # Remove all handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # Reset to default level
    root_logger.setLevel(logging.WARNING)
