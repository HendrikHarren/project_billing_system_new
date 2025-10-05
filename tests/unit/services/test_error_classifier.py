"""
Unit tests for error classification utilities.
"""

import socket
from unittest.mock import Mock

import requests.exceptions
from googleapiclient.errors import HttpError

from src.services.error_classifier import ErrorClassifier, ErrorType


class TestErrorClassifier:
    """Test cases for ErrorClassifier."""

    def test_rate_limit_error_429_is_retryable(self):
        """Test that 429 errors are classified as retryable."""
        error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429, "message": "Rate limit exceeded"}}',
        )

        classifier = ErrorClassifier()
        error_type = classifier.classify(error)

        assert error_type == ErrorType.RETRYABLE
        assert classifier.is_retryable(error)

    def test_server_errors_5xx_are_retryable(self):
        """Test that 5xx errors are classified as retryable."""
        for status in [500, 502, 503, 504]:
            error = HttpError(
                resp=Mock(status=status),
                content=b'{"error": {"message": "Server error"}}',
            )

            classifier = ErrorClassifier()
            assert classifier.is_retryable(error)
            assert classifier.classify(error) == ErrorType.RETRYABLE

    def test_client_errors_4xx_are_fatal(self):
        """Test that 4xx errors (except 429) are classified as fatal."""
        for status in [400, 401, 403, 404]:
            error = HttpError(
                resp=Mock(status=status),
                content=b'{"error": {"message": "Client error"}}',
            )

            classifier = ErrorClassifier()
            assert not classifier.is_retryable(error)
            assert classifier.classify(error) == ErrorType.FATAL

    def test_network_errors_are_retryable(self):
        """Test that network errors are classified as retryable."""
        network_errors = [
            socket.timeout("Connection timed out"),
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Request timed out"),
        ]

        classifier = ErrorClassifier()
        for error in network_errors:
            assert classifier.is_retryable(error)
            assert classifier.classify(error) == ErrorType.RETRYABLE

    def test_unknown_errors_are_unknown(self):
        """Test that unknown errors are classified as unknown."""
        errors = [
            ValueError("Some value error"),
            KeyError("missing_key"),
            RuntimeError("Runtime error"),
        ]

        classifier = ErrorClassifier()
        for error in errors:
            assert not classifier.is_retryable(error)
            assert classifier.classify(error) == ErrorType.UNKNOWN

    def test_get_error_description_for_429(self):
        """Test error description for 429 errors."""
        error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429, "message": "Rate limit exceeded"}}',
        )

        classifier = ErrorClassifier()
        description = classifier.get_error_description(error)

        assert "rate limit" in description.lower()
        assert "429" in description

    def test_get_error_description_for_network_error(self):
        """Test error description for network errors."""
        error = socket.timeout("Connection timed out")

        classifier = ErrorClassifier()
        description = classifier.get_error_description(error)

        assert "network" in description.lower() or "timeout" in description.lower()

    def test_get_error_type_name(self):
        """Test getting error type names."""
        classifier = ErrorClassifier()

        assert classifier.get_error_type_name(ErrorType.RETRYABLE) == "Retryable"
        assert classifier.get_error_type_name(ErrorType.FATAL) == "Fatal"
        assert classifier.get_error_type_name(ErrorType.UNKNOWN) == "Unknown"

    def test_should_log_warning_for_retryable(self):
        """Test that retryable errors should be logged as warnings."""
        error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"code": 429}}',
        )

        classifier = ErrorClassifier()
        # Retryable errors should be logged as warnings (they will be retried)
        assert classifier.classify(error) == ErrorType.RETRYABLE

    def test_should_log_error_for_fatal(self):
        """Test that fatal errors should be logged as errors."""
        error = HttpError(
            resp=Mock(status=404),
            content=b'{"error": {"code": 404}}',
        )

        classifier = ErrorClassifier()
        # Fatal errors should be logged as errors (won't be retried)
        assert classifier.classify(error) == ErrorType.FATAL

    def test_classify_batch_errors(self):
        """Test classifying multiple errors at once."""
        errors = [
            HttpError(resp=Mock(status=429), content=b"{}"),
            HttpError(resp=Mock(status=404), content=b"{}"),
            socket.timeout("timeout"),
            ValueError("value error"),
        ]

        classifier = ErrorClassifier()
        results = classifier.classify_batch(errors)

        assert results[0] == ErrorType.RETRYABLE
        assert results[1] == ErrorType.FATAL
        assert results[2] == ErrorType.RETRYABLE
        assert results[3] == ErrorType.UNKNOWN

    def test_error_statistics(self):
        """Test tracking error statistics."""
        errors = [
            HttpError(resp=Mock(status=429), content=b"{}"),
            HttpError(resp=Mock(status=429), content=b"{}"),
            HttpError(resp=Mock(status=404), content=b"{}"),
            socket.timeout("timeout"),
        ]

        classifier = ErrorClassifier()
        for error in errors:
            classifier.classify(error)

        stats = classifier.get_statistics()
        assert stats["retryable"] == 3  # Two 429s and one timeout
        assert stats["fatal"] == 1  # One 404
        assert stats["unknown"] == 0
        assert stats["total"] == 4
