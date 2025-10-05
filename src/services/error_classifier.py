"""
Error classification utilities for distinguishing retryable from fatal errors.
"""

import logging
import socket
from enum import Enum
from typing import Any, Dict, List

import requests.exceptions
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types."""

    RETRYABLE = "retryable"  # Should be retried (429, 5xx, network errors)
    FATAL = "fatal"  # Should not be retried (4xx except 429, auth errors)
    UNKNOWN = "unknown"  # Unknown error type


class ErrorClassifier:
    """
    Classifies errors to distinguish between retryable and fatal errors.

    Features:
    - HTTP error status code classification
    - Network error detection
    - Error description generation
    - Statistics tracking
    """

    def __init__(self):
        """Initialize error classifier with statistics tracking."""
        self._stats: Dict[str, int] = {
            "retryable": 0,
            "fatal": 0,
            "unknown": 0,
            "total": 0,
        }

    def classify(self, exception: Exception) -> ErrorType:
        """
        Classify an exception into retryable, fatal, or unknown.

        Args:
            exception: The exception to classify

        Returns:
            ErrorType classification
        """
        self._stats["total"] += 1

        # HTTP errors from Google API
        if isinstance(exception, HttpError):
            status_code = exception.resp.status

            # Rate limiting - always retryable
            if status_code == 429:
                self._stats["retryable"] += 1
                return ErrorType.RETRYABLE

            # Server errors (5xx) - retryable
            if 500 <= status_code < 600:
                self._stats["retryable"] += 1
                return ErrorType.RETRYABLE

            # Client errors (4xx except 429) - fatal
            if 400 <= status_code < 500:
                self._stats["fatal"] += 1
                return ErrorType.FATAL

        # Network-related errors - retryable
        if isinstance(
            exception,
            (
                socket.timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ),
        ):
            self._stats["retryable"] += 1
            return ErrorType.RETRYABLE

        # Unknown error type
        self._stats["unknown"] += 1
        return ErrorType.UNKNOWN

    def is_retryable(self, exception: Exception) -> bool:
        """
        Check if an exception should be retried.

        Args:
            exception: The exception to check

        Returns:
            True if retryable, False otherwise
        """
        return self.classify(exception) == ErrorType.RETRYABLE

    def get_error_description(self, exception: Exception) -> str:
        """
        Get a human-readable error description.

        Args:
            exception: The exception to describe

        Returns:
            Error description string
        """
        error_type = self.classify(exception)

        if isinstance(exception, HttpError):
            status_code = exception.resp.status
            if status_code == 429:
                return f"Rate limit error (HTTP 429) - {error_type.value}"
            elif 500 <= status_code < 600:
                return f"Server error (HTTP {status_code}) - {error_type.value}"
            elif 400 <= status_code < 500:
                return f"Client error (HTTP {status_code}) - {error_type.value}"

        if isinstance(exception, (socket.timeout, requests.exceptions.Timeout)):
            return f"Network timeout error - {error_type.value}"

        if isinstance(exception, requests.exceptions.ConnectionError):
            return f"Network connection error - {error_type.value}"

        return f"{type(exception).__name__}: {str(exception)} - {error_type.value}"

    def get_error_type_name(self, error_type: ErrorType) -> str:
        """
        Get human-readable name for error type.

        Args:
            error_type: The error type

        Returns:
            Human-readable name
        """
        return error_type.value.capitalize()

    def classify_batch(self, exceptions: List[Exception]) -> List[ErrorType]:
        """
        Classify multiple exceptions.

        Args:
            exceptions: List of exceptions to classify

        Returns:
            List of error types
        """
        return [self.classify(exc) for exc in exceptions]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get error classification statistics.

        Returns:
            Dictionary with error counts
        """
        return self._stats.copy()

    def reset_statistics(self):
        """Reset error statistics."""
        self._stats = {"retryable": 0, "fatal": 0, "unknown": 0, "total": 0}
