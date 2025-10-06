"""Tests for structured logging utilities."""

import logging
import tempfile
import uuid
from pathlib import Path

import pytest

from src.config.logging_config import LoggingConfig, configure_logging, reset_logging
from src.utils.logging_utils import (
    LogContext,
    generate_correlation_id,
    get_correlation_id,
    log_function_call,
    sanitize_sensitive_data,
)


class TestGenerateCorrelationId:
    """Test correlation ID generation."""

    def test_generate_correlation_id_format(self):
        """Test correlation ID has correct UUID format."""
        corr_id = generate_correlation_id()
        # Should be a valid UUID string
        assert isinstance(corr_id, str)
        # Try to parse as UUID to verify format
        uuid.UUID(corr_id)

    def test_generate_correlation_id_uniqueness(self):
        """Test each correlation ID is unique."""
        ids = [generate_correlation_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


class TestLogContext:
    """Test LogContext context manager."""

    def teardown_method(self):
        """Reset logging after each test."""
        reset_logging()

    def test_context_adds_fields_to_logs(self):
        """Test context manager adds fields to log records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            logger = logging.getLogger("test_module")

            with LogContext(freelancer_name="John Doe", project_code="PROJ001"):
                logger.info("Test message")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            content = log_file.read_text().strip()
            log_entry = json.loads(content)

            assert log_entry["freelancer_name"] == "John Doe"
            assert log_entry["project_code"] == "PROJ001"

    def test_context_nesting(self):
        """Test nested contexts merge fields correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            logger = logging.getLogger("test_module")

            with LogContext(freelancer_name="John Doe"):
                with LogContext(project_code="PROJ001"):
                    logger.info("Nested message")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            content = log_file.read_text().strip()
            log_entry = json.loads(content)

            # Both contexts should be present
            assert log_entry["freelancer_name"] == "John Doe"
            assert log_entry["project_code"] == "PROJ001"

    def test_context_cleanup_after_exit(self):
        """Test context fields are removed after exiting context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            logger = logging.getLogger("test_module")

            # Log inside context
            with LogContext(freelancer_name="John Doe"):
                logger.info("Inside context")

            # Log outside context
            logger.info("Outside context")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            lines = log_file.read_text().strip().split("\n")
            inside_entry = json.loads(lines[0])
            outside_entry = json.loads(lines[1])

            # Inside should have field
            assert "freelancer_name" in inside_entry

            # Outside should not have field
            assert "freelancer_name" not in outside_entry

    def test_context_with_correlation_id(self):
        """Test context can add correlation ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            logger = logging.getLogger("test_module")
            corr_id = generate_correlation_id()

            with LogContext(correlation_id=corr_id):
                logger.info("Message with correlation ID")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            content = log_file.read_text().strip()
            log_entry = json.loads(content)

            assert log_entry["correlation_id"] == corr_id

    def test_get_correlation_id_from_context(self):
        """Test retrieving correlation ID from context."""
        corr_id = generate_correlation_id()

        with LogContext(correlation_id=corr_id):
            assert get_correlation_id() == corr_id

    def test_get_correlation_id_outside_context(self):
        """Test getting correlation ID outside context returns None."""
        assert get_correlation_id() is None


class TestSanitizeSensitiveData:
    """Test sensitive data sanitization."""

    def test_sanitize_password(self):
        """Test password field is sanitized."""
        data = {"username": "john", "password": "secret123"}
        sanitized = sanitize_sensitive_data(data)

        assert sanitized["username"] == "john"
        assert sanitized["password"] == "***REDACTED***"

    def test_sanitize_api_key(self):
        """Test API key is sanitized."""
        data = {"api_key": "sk_live_123456", "user": "john"}
        sanitized = sanitize_sensitive_data(data)

        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["user"] == "john"

    def test_sanitize_nested_dict(self):
        """Test nested dictionaries are sanitized."""
        data = {"user": {"name": "john", "token": "abc123"}}
        sanitized = sanitize_sensitive_data(data)

        assert sanitized["user"]["name"] == "john"
        assert sanitized["user"]["token"] == "***REDACTED***"

    def test_sanitize_preserves_non_sensitive(self):
        """Test non-sensitive fields are preserved."""
        data = {
            "freelancer_name": "John Doe",
            "project_code": "PROJ001",
            "hours": 8.5,
        }
        sanitized = sanitize_sensitive_data(data)

        assert sanitized == data

    def test_sanitize_handles_none(self):
        """Test sanitization handles None values."""
        data = {"username": "john", "password": None}
        sanitized = sanitize_sensitive_data(data)

        assert sanitized["password"] is None


class TestLogFunctionCall:
    """Test function call logging decorator."""

    def teardown_method(self):
        """Reset logging after each test."""
        reset_logging()

    def test_log_function_call_logs_entry_exit(self):
        """Test decorator logs function entry and exit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="DEBUG",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            @log_function_call
            def test_function(x, y):
                return x + y

            result = test_function(2, 3)

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 2

            entry_log = json.loads(lines[0])
            exit_log = json.loads(lines[1])

            assert "Entering test_function" in entry_log["message"]
            assert "Exiting test_function" in exit_log["message"]
            assert result == 5

    def test_log_function_call_includes_args(self):
        """Test decorator includes function arguments in logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="DEBUG",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            @log_function_call(include_args=True)
            def test_function(name, age):
                return f"{name} is {age}"

            test_function("John", 30)

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            lines = log_file.read_text().strip().split("\n")
            entry_log = json.loads(lines[0])

            assert "args" in entry_log or "John" in entry_log["message"]

    def test_log_function_call_exception_handling(self):
        """Test decorator logs exceptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="DEBUG",
                log_format="json",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            @log_function_call
            def failing_function():
                raise ValueError("Test error")

            with pytest.raises(ValueError):
                failing_function()

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            lines = log_file.read_text().strip().split("\n")
            # Should have entry and error logs
            assert len(lines) >= 2

            # Last log should be error
            error_log = json.loads(lines[-1])
            assert error_log["level"] == "ERROR"
            assert "ValueError" in str(error_log.get("message", ""))
