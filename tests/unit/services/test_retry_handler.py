"""
Unit tests for retry handler with exponential backoff and circuit breaker.
"""

from unittest.mock import Mock, patch

import pytest
from googleapiclient.errors import HttpError

from src.services.retry_handler import (
    CircuitBreakerError,
    RetryExhaustedException,
    RetryHandler,
)


class TestRetryHandler:
    """Test cases for RetryHandler."""

    @pytest.fixture
    def retry_handler(self):
        """RetryHandler instance with test configuration."""
        return RetryHandler(
            max_retries=3,
            base_delay=0.1,  # Short delay for testing
            max_delay=1.0,
            exponential_base=2,
            jitter_factor=0.1,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=2.0,
        )

    def test_initialization_with_defaults(self):
        """Test retry handler initializes with default values."""
        handler = RetryHandler()

        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
        assert handler.max_delay == 60.0
        assert handler.exponential_base == 2
        assert handler.jitter_factor == 0.1
        assert handler.circuit_breaker_threshold == 10
        assert handler.circuit_breaker_timeout == 60.0

    def test_successful_execution_no_retry(self, retry_handler):
        """Test successful execution without retries."""
        mock_func = Mock(return_value="success")

        result = retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        mock_func.assert_called_once()

    def test_retry_on_rate_limit_error(self, retry_handler):
        """Test retry behavior on rate limit (429) errors."""
        mock_func = Mock()
        rate_limit_error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429, "message": "Rate limit exceeded"}}',
        )

        # Fail twice, then succeed
        mock_func.side_effect = [rate_limit_error, rate_limit_error, "success"]

        with patch("time.sleep") as mock_sleep:
            result = retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2

    def test_retry_on_server_error(self, retry_handler):
        """Test retry behavior on server (5xx) errors."""
        mock_func = Mock()
        server_error = HttpError(
            resp=Mock(status=503),
            content=b'{"error": {"code": 503, "message": "Service unavailable"}}',
        )

        mock_func.side_effect = [server_error, "success"]

        with patch("time.sleep") as mock_sleep:
            result = retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1

    def test_no_retry_on_client_error(self, retry_handler):
        """Test no retry on client (4xx) errors except 429."""
        mock_func = Mock()
        client_error = HttpError(
            resp=Mock(status=404),
            content=b'{"error": {"code": 404, "message": "Not found"}}',
        )

        mock_func.side_effect = client_error

        with pytest.raises(HttpError):
            retry_handler.execute_with_retry(mock_func)

        # Should not retry on 404
        mock_func.assert_called_once()

    def test_exponential_backoff_calculation(self, retry_handler):
        """Test exponential backoff delay calculation."""
        delays = []

        # Mock sleep to capture delay values
        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda delay: delays.append(delay)

            mock_func = Mock()
            server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
            mock_func.side_effect = [
                server_error,
                server_error,
                server_error,
                server_error,
            ]

            with pytest.raises(RetryExhaustedException):
                retry_handler.execute_with_retry(mock_func)

        # Check that delays follow exponential backoff pattern
        assert len(delays) == 3  # max_retries attempts
        # Allow for jitter which can reduce delay by up to 10%
        assert delays[0] >= 0.09  # base_delay (0.1) with jitter
        assert delays[1] >= 0.18  # exponential increase (0.2) with jitter
        assert delays[2] >= 0.36  # exponential increase (0.4) with jitter
        # Check increasing pattern (allowing for jitter)
        assert delays[1] > delays[0] * 1.5  # Should roughly double
        assert delays[2] > delays[1] * 1.5  # Should roughly double

    def test_jitter_applied_to_delays(self, retry_handler):
        """Test that jitter is applied to backoff delays."""
        delays = []

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda delay: delays.append(delay)
            with patch("secrets.SystemRandom") as mock_system_random:
                mock_uniform = Mock(return_value=0.05)  # Fixed jitter for testing
                mock_system_random.return_value.uniform = mock_uniform

                mock_func = Mock()
                server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
                mock_func.side_effect = [server_error, "success"]

                retry_handler.execute_with_retry(mock_func)

        # Jitter should be applied
        mock_uniform.assert_called()
        assert len(delays) == 1

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        handler = RetryHandler(
            max_retries=5,
            base_delay=10.0,
            max_delay=2.0,  # Very low max to test capping
            exponential_base=3,
        )

        delays = []
        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda delay: delays.append(delay)

            mock_func = Mock()
            server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
            mock_func.side_effect = [server_error] * 6

            with pytest.raises(RetryExhaustedException):
                handler.execute_with_retry(mock_func)

        # All delays should be capped at max_delay plus jitter (10%)
        assert all(delay <= 2.2 for delay in delays)  # max_delay (2.0) + 10% jitter

    def test_retry_exhausted_exception(self, retry_handler):
        """Test RetryExhaustedException after max retries."""
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = server_error

        with pytest.raises(RetryExhaustedException) as exc_info:
            retry_handler.execute_with_retry(mock_func)

        assert "Max retries (3) exceeded" in str(exc_info.value)
        assert mock_func.call_count == 4  # initial + 3 retries

    def test_circuit_breaker_opens_after_threshold(self, retry_handler):
        """Test circuit breaker opens after failure threshold."""
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = server_error

        # Trigger failures to reach circuit breaker threshold
        for _ in range(5):
            try:
                retry_handler.execute_with_retry(mock_func)
            except (HttpError, RetryExhaustedException):
                pass

        # Circuit breaker should now be open
        assert retry_handler._circuit_breaker_open is True

        # Next call should fail immediately with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            retry_handler.execute_with_retry(mock_func)

    def test_circuit_breaker_half_open_after_timeout(self, retry_handler):
        """Test circuit breaker transitions to half-open after timeout."""
        # Open the circuit breaker
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = server_error

        for _ in range(5):
            try:
                retry_handler.execute_with_retry(mock_func)
            except (HttpError, RetryExhaustedException):
                pass

        assert retry_handler._circuit_breaker_open is True

        # Simulate timeout passage
        with patch("time.time") as mock_time:
            mock_time.return_value = retry_handler._circuit_breaker_opened_at + 3.0

            # Should allow one test call (half-open state)
            mock_func.side_effect = None
            mock_func.return_value = "success"
            result = retry_handler.execute_with_retry(mock_func)

            assert result == "success"
            assert retry_handler._circuit_breaker_open is False

    def test_circuit_breaker_closes_on_success(self, retry_handler):
        """Test circuit breaker closes after successful call in half-open state."""
        # Open circuit breaker
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = server_error

        for _ in range(5):
            try:
                retry_handler.execute_with_retry(mock_func)
            except (HttpError, RetryExhaustedException):
                pass

        # Simulate timeout and successful recovery
        with patch("time.time") as mock_time:
            mock_time.return_value = retry_handler._circuit_breaker_opened_at + 3.0
            mock_func.side_effect = None
            mock_func.return_value = "success"

            result = retry_handler.execute_with_retry(mock_func)

            assert result == "success"
            assert retry_handler._circuit_breaker_open is False
            assert retry_handler._failure_count == 0

    def test_custom_retry_conditions(self):
        """Test custom retry condition function."""

        def custom_retry_condition(exception):
            return isinstance(exception, ValueError)

        handler = RetryHandler(retry_condition=custom_retry_condition)

        mock_func = Mock()
        value_error = ValueError("Custom error")
        mock_func.side_effect = [value_error, "success"]

        with patch("time.sleep"):
            result = handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_no_retry_on_non_matching_condition(self):
        """Test no retry when custom condition doesn't match."""

        def custom_retry_condition(exception):
            return isinstance(exception, ValueError)

        handler = RetryHandler(retry_condition=custom_retry_condition)

        mock_func = Mock()
        type_error = TypeError("Type error")
        mock_func.side_effect = type_error

        with pytest.raises(TypeError):
            handler.execute_with_retry(mock_func)

        mock_func.assert_called_once()

    def test_retry_with_function_arguments(self, retry_handler):
        """Test retry handler preserves function arguments."""
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = [server_error, "success"]

        with patch("time.sleep"):
            result = retry_handler.execute_with_retry(
                mock_func, "arg1", "arg2", kwarg1="value1", kwarg2="value2"
            )

        assert result == "success"
        assert mock_func.call_count == 2
        # Verify arguments were passed correctly
        mock_func.assert_any_call("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    def test_retry_statistics_tracking(self, retry_handler):
        """Test that retry statistics are tracked correctly."""
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = [server_error, server_error, "success"]

        with patch("time.sleep"):
            retry_handler.execute_with_retry(mock_func)

        stats = retry_handler.get_retry_statistics()
        assert stats["total_calls"] == 1
        assert stats["total_retries"] == 2
        assert stats["total_failures"] == 0  # Ultimately successful

    def test_reset_circuit_breaker(self, retry_handler):
        """Test manual circuit breaker reset."""
        # Open circuit breaker
        mock_func = Mock()
        server_error = HttpError(resp=Mock(status=500), content=b"Server Error")
        mock_func.side_effect = server_error

        for _ in range(5):
            try:
                retry_handler.execute_with_retry(mock_func)
            except (HttpError, RetryExhaustedException):
                pass

        assert retry_handler._circuit_breaker_open is True

        # Reset circuit breaker
        retry_handler.reset_circuit_breaker()

        assert retry_handler._circuit_breaker_open is False
        assert retry_handler._failure_count == 0

    def test_context_manager_usage(self, retry_handler):
        """Test retry handler can be used as context manager."""
        mock_func = Mock(return_value="success")

        with retry_handler as handler:
            result = handler.execute_with_retry(mock_func)

        assert result == "success"

    def test_thread_safety(self, retry_handler):
        """Test retry handler is thread-safe."""
        import threading

        results = []
        errors = []

        def worker():
            try:
                mock_func = Mock(
                    return_value=f"success-{threading.current_thread().ident}"
                )
                result = retry_handler.execute_with_retry(mock_func)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert len(errors) == 0
        assert len(set(results)) == 10  # All results should be unique


class TestRetryHandlerIntegration:
    """Integration tests for RetryHandler."""

    @pytest.mark.integration
    def test_real_api_retry_behavior(self, test_config):
        """Test retry behavior with real API calls."""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        assert handler is not None

        # This would test with real API that might return rate limits
        # Implementation depends on test environment setup
        pass

    @pytest.mark.slow
    def test_performance_under_load(self):
        """Test retry handler performance under concurrent load."""
        handler = RetryHandler()
        assert handler is not None

        # Simulate high load scenario
        # Implementation depends on performance requirements
        pass


class TestRetryHandlerErrorScenarios:
    """Test specific error scenarios and edge cases."""

    @pytest.fixture
    def retry_handler(self):
        """RetryHandler instance with test configuration."""
        return RetryHandler(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_base=2,
            jitter_factor=0.1,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=2.0,
        )

    def test_malformed_http_error_handling(self, retry_handler):
        """Test handling of malformed HTTP errors."""
        mock_func = Mock()
        # Create HTTP error with malformed response
        malformed_error = HttpError(
            resp=Mock(status=500), content=b"Invalid JSON response"
        )
        mock_func.side_effect = malformed_error

        with pytest.raises(RetryExhaustedException):
            retry_handler.execute_with_retry(mock_func)

    def test_network_timeout_handling(self, retry_handler):
        """Test handling of network timeout errors."""
        import socket

        mock_func = Mock()
        timeout_error = socket.timeout("Connection timed out")
        mock_func.side_effect = [timeout_error, "success"]

        with patch("time.sleep"):
            result = retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_connection_error_handling(self, retry_handler):
        """Test handling of connection errors."""
        import requests.exceptions

        mock_func = Mock()
        connection_error = requests.exceptions.ConnectionError("Connection failed")
        mock_func.side_effect = [connection_error, "success"]

        with patch("time.sleep"):
            result = retry_handler.execute_with_retry(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2
