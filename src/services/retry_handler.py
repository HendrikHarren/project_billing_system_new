"""
Retry handler with exponential backoff, jitter, and circuit breaker pattern.
"""

import logging
import random
import socket
import threading
import time
from typing import Any, Callable, Optional

import requests.exceptions
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class RetryExhaustedException(Exception):
    """Raised when all retry attempts have been exhausted."""

    pass


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class RetryHandler:
    """
    Handles retries with exponential backoff, jitter, and circuit breaker pattern.

    Features:
    - Exponential backoff with configurable base and jitter
    - Circuit breaker to prevent cascade failures
    - Thread-safe operation
    - Configurable retry conditions
    - Statistics tracking
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2,
        jitter_factor: float = 0.1,
        circuit_breaker_threshold: int = 10,
        circuit_breaker_timeout: float = 60.0,
        retry_condition: Optional[Callable[[Exception], bool]] = None,
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff calculation
            jitter_factor: Factor for random jitter (0.0 to 1.0)
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Time to wait before trying again (seconds)
            retry_condition: Custom function to determine if retry should occur
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter_factor = jitter_factor
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.retry_condition = retry_condition or self._default_retry_condition

        # Circuit breaker state
        self._circuit_breaker_open = False
        self._circuit_breaker_opened_at = 0.0
        self._failure_count = 0

        # Statistics
        self._total_calls = 0
        self._total_retries = 0
        self._total_failures = 0

        # Thread safety
        self._lock = threading.Lock()

    def _default_retry_condition(self, exception: Exception) -> bool:
        """
        Default retry condition - retry on transient errors.

        Args:
            exception: The exception that occurred

        Returns:
            True if retry should be attempted, False otherwise
        """
        # Retry on HTTP 429 (rate limit) and 5xx (server errors)
        if isinstance(exception, HttpError):
            status_code = exception.resp.status
            return status_code == 429 or 500 <= status_code < 600

        # Retry on network-related errors
        if isinstance(exception, (socket.timeout, requests.exceptions.ConnectionError)):
            return True

        return False

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff with jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = self.base_delay * (self.exponential_base**attempt)

        # Apply maximum delay cap
        delay = min(delay, self.max_delay)

        # Add jitter
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * delay
        delay = max(0, delay + jitter)

        return delay

    def _is_circuit_breaker_open(self) -> bool:
        """
        Check if circuit breaker is open.

        Returns:
            True if circuit breaker is open, False otherwise
        """
        with self._lock:
            if not self._circuit_breaker_open:
                return False

            # Check if timeout has passed (transition to half-open)
            if (
                time.time() - self._circuit_breaker_opened_at
                >= self.circuit_breaker_timeout
            ):
                logger.info("Circuit breaker transitioning to half-open state")
                return False

            return True

    def _record_success(self):
        """Record successful execution - closes circuit breaker."""
        with self._lock:
            self._failure_count = 0
            if self._circuit_breaker_open:
                logger.info("Circuit breaker closed after successful execution")
                self._circuit_breaker_open = False

    def _record_failure(self):
        """Record failed execution - may open circuit breaker."""
        with self._lock:
            self._failure_count += 1

            if (
                not self._circuit_breaker_open
                and self._failure_count >= self.circuit_breaker_threshold
            ):

                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )
                self._circuit_breaker_open = True
                self._circuit_breaker_opened_at = time.time()

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function execution

        Raises:
            CircuitBreakerError: If circuit breaker is open
            RetryExhaustedException: If all retries are exhausted
            Exception: Original exception if not retryable
        """
        with self._lock:
            self._total_calls += 1

        # Check circuit breaker
        if self._is_circuit_breaker_open():
            raise CircuitBreakerError("Circuit breaker is open")

        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                result = func(*args, **kwargs)

                # Success - record and return
                if attempt > 0:  # Only log if there were retries
                    func_name = getattr(func, "__name__", repr(func))
                    logger.info(
                        f"Function {func_name} succeeded after {attempt} retries"
                    )
                    with self._lock:
                        self._total_retries += attempt

                self._record_success()
                return result

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not self.retry_condition(e):
                    logger.debug(
                        f"Not retrying - condition not met: {type(e).__name__}"
                    )
                    raise e

                # Check if we have retries left
                if attempt >= self.max_retries:
                    func_name = getattr(func, "__name__", repr(func))
                    logger.warning(
                        f"Max retries ({self.max_retries}) exceeded for {func_name}"
                    )
                    with self._lock:
                        self._total_retries += attempt
                        self._total_failures += 1

                    self._record_failure()
                    raise RetryExhaustedException(
                        f"Max retries ({self.max_retries}) exceeded. "
                        f"Last error: {type(e).__name__}: {e}"
                    )

                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                func_name = getattr(func, "__name__", repr(func))
                logger.debug(
                    f"Retrying {func_name} in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries + 1}). "
                    f"Error: {type(e).__name__}: {e}"
                )

                time.sleep(delay)

        # This should never be reached, but just in case
        self._record_failure()
        raise last_exception

    def get_retry_statistics(self) -> dict:
        """
        Get retry statistics.

        Returns:
            Dictionary with retry statistics
        """
        with self._lock:
            return {
                "total_calls": self._total_calls,
                "total_retries": self._total_retries,
                "total_failures": self._total_failures,
                "circuit_breaker_open": self._circuit_breaker_open,
                "failure_count": self._failure_count,
            }

    def reset_circuit_breaker(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._circuit_breaker_open = False
            self._failure_count = 0
            self._circuit_breaker_opened_at = 0.0

        logger.info("Circuit breaker manually reset")

    def reset_statistics(self):
        """Reset retry statistics."""
        with self._lock:
            self._total_calls = 0
            self._total_retries = 0
            self._total_failures = 0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
