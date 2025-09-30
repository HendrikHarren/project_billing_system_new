"""
Smoke tests for Google API services to verify basic functionality.
"""

from unittest.mock import Mock

import pytest

from src.services.retry_handler import RetryExhaustedException, RetryHandler


class TestServicesSmoke:
    """Basic smoke tests to verify services can be instantiated and work."""

    def test_retry_handler_basic_functionality(self):
        """Test that retry handler works for basic operations."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        # Test successful execution
        mock_func = Mock(return_value="success")
        result = handler.execute_with_retry(mock_func)
        assert result == "success"

        # Test statistics
        stats = handler.get_retry_statistics()
        assert stats["total_calls"] == 1
        assert stats["total_retries"] == 0
        assert stats["total_failures"] == 0

    def test_retry_handler_with_retries(self):
        """Test retry handler with actual retries using custom condition."""

        # Use custom retry condition that retries on all exceptions
        def retry_all_exceptions(exception):
            return True

        handler = RetryHandler(
            max_retries=2, base_delay=0.01, retry_condition=retry_all_exceptions
        )

        # Create function that fails twice then succeeds
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])

        result = handler.execute_with_retry(mock_func)
        assert result == "success"

        # Verify statistics
        stats = handler.get_retry_statistics()
        assert stats["total_calls"] == 1
        assert stats["total_retries"] == 2
        assert stats["total_failures"] == 0
        assert mock_func.call_count == 3

    def test_retry_handler_exhaustion(self):
        """Test retry handler when retries are exhausted."""

        # Use custom retry condition that retries on all exceptions
        def retry_all_exceptions(exception):
            return True

        handler = RetryHandler(
            max_retries=2, base_delay=0.01, retry_condition=retry_all_exceptions
        )

        # Create function that always fails
        mock_func = Mock(side_effect=Exception("Always fails"))

        with pytest.raises(RetryExhaustedException):
            handler.execute_with_retry(mock_func)

        # Verify statistics
        stats = handler.get_retry_statistics()
        assert stats["total_calls"] == 1
        assert stats["total_retries"] == 2
        assert stats["total_failures"] == 1
        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern works."""

        # Use custom retry condition that retries on all exceptions
        def retry_all_exceptions(exception):
            return True

        handler = RetryHandler(
            max_retries=1,
            base_delay=0.01,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=0.1,
            retry_condition=retry_all_exceptions,
        )

        # Create a function that always fails
        mock_func = Mock(side_effect=Exception("Always fails"))

        # First call should exhaust retries
        with pytest.raises(RetryExhaustedException):
            handler.execute_with_retry(mock_func)

        # Second call should also exhaust retries and trigger circuit breaker
        with pytest.raises(RetryExhaustedException):
            handler.execute_with_retry(mock_func)

        # Verify circuit breaker state
        stats = handler.get_retry_statistics()
        assert stats["circuit_breaker_open"] is True
        assert stats["failure_count"] == 2

    def test_services_can_be_imported(self):
        """Test that all services can be imported successfully."""
        from src.services.google_drive_service import GoogleDriveService
        from src.services.google_sheets_service import GoogleSheetsService
        from src.services.retry_handler import (
            CircuitBreakerError,
            RetryExhaustedException,
            RetryHandler,
        )

        # Verify all classes are available
        assert RetryHandler is not None
        assert GoogleSheetsService is not None
        assert GoogleDriveService is not None
        assert RetryExhaustedException is not None
        assert CircuitBreakerError is not None

    def test_retry_handler_context_manager(self):
        """Test retry handler as context manager."""
        with RetryHandler(max_retries=1, base_delay=0.01) as handler:
            mock_func = Mock(return_value="context_success")
            result = handler.execute_with_retry(mock_func)
            assert result == "context_success"

    def test_retry_handler_statistics_reset(self):
        """Test retry handler statistics can be reset."""
        handler = RetryHandler(max_retries=1, base_delay=0.01)

        # Execute some operations
        mock_func = Mock(return_value="test")
        handler.execute_with_retry(mock_func)

        # Verify statistics
        stats = handler.get_retry_statistics()
        assert stats["total_calls"] == 1

        # Reset and verify
        handler.reset_statistics()
        stats = handler.get_retry_statistics()
        assert stats["total_calls"] == 0
        assert stats["total_retries"] == 0
        assert stats["total_failures"] == 0
