"""Tests for centralized logging configuration."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.logging_config import (
    JSONFormatter,
    LoggingConfig,
    configure_logging,
    get_logger,
    reset_logging,
)


class TestLoggingConfig:
    """Test LoggingConfig class."""

    def test_default_configuration(self):
        """Test default logging configuration."""
        config = LoggingConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "standard"
        assert config.log_file is None
        assert config.enable_console is True
        assert config.enable_file is False
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5

    def test_environment_variable_override(self):
        """Test configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "json",
                "LOG_FILE": "/tmp/test.log",
                "LOG_MAX_FILE_SIZE": "5242880",  # 5MB
                "LOG_BACKUP_COUNT": "3",
            },
        ):
            config = LoggingConfig.from_env()

            assert config.log_level == "DEBUG"
            assert config.log_format == "json"
            assert config.log_file == "/tmp/test.log"
            assert config.max_file_size == 5242880
            assert config.backup_count == 3

    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(log_level="INVALID")

    def test_invalid_log_format(self):
        """Test invalid log format raises error."""
        with pytest.raises(ValueError, match="Invalid log format"):
            LoggingConfig(log_format="invalid")

    def test_file_logging_enabled_without_path(self):
        """Test file logging enabled without file path raises error."""
        with pytest.raises(ValueError, match="log_file must be specified"):
            LoggingConfig(enable_file=True, log_file=None)


class TestConfigureLogging:
    """Test configure_logging function."""

    def teardown_method(self):
        """Reset logging after each test."""
        reset_logging()

    def test_console_handler_configuration(self):
        """Test console handler is configured correctly."""
        config = LoggingConfig(log_level="DEBUG", enable_console=True)
        configure_logging(config)

        root_logger = logging.getLogger()

        # Verify StreamHandler was added
        stream_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) == 1

        # Verify level is set correctly
        assert root_logger.level == logging.DEBUG

    def test_log_level_filtering(self):
        """Test log level filtering works correctly."""
        config = LoggingConfig(log_level="WARNING", enable_console=True)
        configure_logging(config)

        root_logger = logging.getLogger()

        # Verify root logger level is WARNING
        assert root_logger.level == logging.WARNING

        # Verify handler level is WARNING
        for handler in root_logger.handlers:
            assert handler.level == logging.WARNING

    def test_file_handler_configuration(self):
        """Test file handler is configured correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
            )
            configure_logging(config)

            logger = get_logger("test_module")
            logger.info("Test file message")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            assert log_file.exists()
            content = log_file.read_text()
            assert "Test file message" in content

    def test_standard_format(self):
        """Test standard log format."""
        config = LoggingConfig(log_level="INFO", log_format="standard")
        configure_logging(config)

        root_logger = logging.getLogger()

        # Verify formatter is set
        for handler in root_logger.handlers:
            assert handler.formatter is not None
            # Standard formatter should be a regular Formatter, not JSONFormatter
            assert not isinstance(handler.formatter, JSONFormatter)

    def test_json_format_structure(self):
        """Test JSON log format structure."""
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

            logger = get_logger("test_module")
            logger.info("JSON format test", extra={"custom_field": "value"})

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            import json

            content = log_file.read_text()
            log_entry = json.loads(content.strip())

            assert log_entry["level"] == "INFO"
            assert log_entry["logger"] == "test_module"
            assert log_entry["message"] == "JSON format test"
            assert log_entry["custom_field"] == "value"

    def test_rotating_file_handler(self):
        """Test rotating file handler configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            config = LoggingConfig(
                log_level="INFO",
                enable_console=False,
                enable_file=True,
                log_file=str(log_file),
                max_file_size=100,  # Very small for testing
                backup_count=2,
            )
            configure_logging(config)

            logger = get_logger("test_module")

            # Write enough to trigger rotation
            for i in range(50):
                logger.info(f"Log message {i} with some padding to increase size")

            # Force flush
            for handler in logging.getLogger().handlers:
                handler.flush()

            # Check backup files were created
            backup_files = list(Path(tmpdir).glob("test.log.*"))
            assert len(backup_files) > 0

    def test_multiple_loggers_same_config(self):
        """Test multiple loggers use same configuration."""
        config = LoggingConfig(log_level="DEBUG")
        configure_logging(config)

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Child loggers inherit level from root logger (level 0 = NOTSET means inherit)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert logger1.getEffectiveLevel() == logging.DEBUG
        assert logger2.getEffectiveLevel() == logging.DEBUG

    def test_reconfiguration(self):
        """Test reconfiguration replaces handlers."""
        # Initial configuration
        config1 = LoggingConfig(log_level="INFO")
        configure_logging(config1)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        initial_handler_count = len(root_logger.handlers)

        # Reconfigure with different level
        config2 = LoggingConfig(log_level="DEBUG")
        configure_logging(config2)

        # Verify level changed
        assert root_logger.level == logging.DEBUG

        # Verify same number of handlers (old ones removed, new ones added)
        assert len(root_logger.handlers) == initial_handler_count


class TestGetLogger:
    """Test get_logger function."""

    def teardown_method(self):
        """Reset logging after each test."""
        reset_logging()

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_caching(self):
        """Test get_logger returns same instance for same name."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2

    def test_get_logger_before_configuration(self):
        """Test get_logger works before configure_logging is called."""
        logger = get_logger("test_module")
        # Should not raise an error
        logger.info("Test message")


class TestResetLogging:
    """Test reset_logging function."""

    def test_reset_removes_handlers(self):
        """Test reset_logging removes all handlers."""
        config = LoggingConfig(log_level="INFO")
        configure_logging(config)

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

        reset_logging()

        assert len(root_logger.handlers) == 0

    def test_reset_sets_default_level(self):
        """Test reset_logging sets level to WARNING."""
        config = LoggingConfig(log_level="DEBUG")
        configure_logging(config)

        reset_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
