#!/usr/bin/env python
"""
Demo script for Issue #18: Error Handling & Logging

This script demonstrates the new logging and error handling features:
1. Centralized logging configuration
2. Structured logging with context
3. Correlation IDs for request tracking
4. Sensitive data sanitization
5. Function call logging decorator
"""

import tempfile
from pathlib import Path

from src.config.logging_config import LoggingConfig, configure_logging, get_logger
from src.utils.logging_utils import (
    LogContext,
    generate_correlation_id,
    log_function_call,
    sanitize_sensitive_data,
)


def demo_basic_logging():
    """Demonstrate basic logging configuration."""
    print("\n" + "=" * 60)
    print("DEMO 1: Basic Logging Configuration")
    print("=" * 60)

    # Configure logging with standard format and INFO level
    config = LoggingConfig(log_level="INFO", log_format="standard")
    configure_logging(config)

    logger = get_logger(__name__)

    logger.debug("This won't appear (level is INFO)")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    print("\n✅ Basic logging configured successfully")


def demo_json_logging():
    """Demonstrate JSON structured logging."""
    print("\n" + "=" * 60)
    print("DEMO 2: JSON Structured Logging")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "demo.log"

        # Configure JSON logging to file
        config = LoggingConfig(
            log_level="INFO",
            log_format="json",
            enable_console=False,
            enable_file=True,
            log_file=str(log_file),
        )
        configure_logging(config)

        logger = get_logger(__name__)
        logger.info(
            "JSON formatted log entry", extra={"user": "demo", "action": "test"}
        )

        # Force flush
        import logging

        for handler in logging.getLogger().handlers:
            handler.flush()

        # Read and display
        content = log_file.read_text()
        print("JSON log entry:")
        print(content)

    print("\n✅ JSON logging demonstrated")


def demo_context_logging():
    """Demonstrate context-based structured logging."""
    print("\n" + "=" * 60)
    print("DEMO 3: Context-Based Structured Logging")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "demo.log"

        config = LoggingConfig(
            log_level="INFO",
            log_format="json",
            enable_console=False,
            enable_file=True,
            log_file=str(log_file),
        )
        configure_logging(config)

        logger = get_logger(__name__)

        # Use context to add fields to all log entries
        with LogContext(freelancer_name="John Doe", project_code="PROJ001"):
            logger.info("Processing timesheet entry")
            logger.info("Calculating billing")

        # Force flush
        import logging

        for handler in logging.getLogger().handlers:
            handler.flush()

        # Display
        import json

        print("Logs with context fields:")
        for line in log_file.read_text().strip().split("\n"):
            entry = json.loads(line)
            print(
                f"  - {entry['message']} "
                f"[freelancer={entry.get('freelancer_name')}, "
                f"project={entry.get('project_code')}]"
            )

    print("\n✅ Context logging demonstrated")


def demo_correlation_ids():
    """Demonstrate correlation ID tracking."""
    print("\n" + "=" * 60)
    print("DEMO 4: Correlation ID Tracking")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "demo.log"

        config = LoggingConfig(
            log_level="INFO",
            log_format="json",
            enable_console=False,
            enable_file=True,
            log_file=str(log_file),
        )
        configure_logging(config)

        logger = get_logger(__name__)

        # Generate correlation ID
        corr_id = generate_correlation_id()
        print(f"Generated correlation ID: {corr_id}")

        # Use correlation ID in context
        with LogContext(correlation_id=corr_id):
            logger.info("Request started")
            logger.info("Processing data")
            logger.info("Request completed")

        # Force flush
        import logging

        for handler in logging.getLogger().handlers:
            handler.flush()

        # Display
        import json

        print("\nLogs with correlation ID:")
        for line in log_file.read_text().strip().split("\n"):
            entry = json.loads(line)
            print(f"  - [{entry.get('correlation_id')[:8]}...] {entry['message']}")

    print("\n✅ Correlation ID tracking demonstrated")


def demo_sensitive_data_sanitization():
    """Demonstrate sensitive data sanitization."""
    print("\n" + "=" * 60)
    print("DEMO 5: Sensitive Data Sanitization")
    print("=" * 60)

    # Sensitive data example
    user_data = {
        "username": "john.doe",
        "email": "john@example.com",
        "password": "super_secret_123",
        "api_key": "sk_live_abc123def456",
        "profile": {"name": "John Doe", "token": "user_token_xyz"},
    }

    print("Original data:")
    print(f"  {user_data}")

    sanitized = sanitize_sensitive_data(user_data)

    print("\nSanitized data:")
    print(f"  {sanitized}")

    print("\n✅ Sensitive data sanitized successfully")


@log_function_call(include_args=True, level="INFO")
def calculate_billing(hours: float, rate: float) -> float:
    """Example function with logging decorator."""
    return hours * rate


def demo_function_logging():
    """Demonstrate function call logging."""
    print("\n" + "=" * 60)
    print("DEMO 6: Function Call Logging")
    print("=" * 60)

    # Configure logging
    config = LoggingConfig(log_level="INFO", log_format="standard")
    configure_logging(config)

    print("\nCalling calculate_billing(8.5, 100.0)...")
    result = calculate_billing(8.5, 100.0)
    print(f"Result: ${result}")

    print("\n✅ Function logging demonstrated")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Issue #18: Error Handling & Logging - Demo")
    print("=" * 60)

    demo_basic_logging()
    demo_json_logging()
    demo_context_logging()
    demo_correlation_ids()
    demo_sensitive_data_sanitization()
    demo_function_logging()

    print("\n" + "=" * 60)
    print("All demos completed successfully! ✅")
    print("=" * 60)
    print(
        "\nTo use these features in your code:"
        "\n1. Configure logging in your application entry point"
        "\n2. Use LogContext to add structured fields"
        "\n3. Generate correlation IDs for request tracking"
        "\n4. Sanitize sensitive data before logging"
        "\n5. Use @log_function_call decorator for debugging"
        "\n\nSee docs/LOGGING.md for more details."
    )


if __name__ == "__main__":
    main()
