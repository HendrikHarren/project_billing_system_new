"""Validation report for collecting and formatting validation issues."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional


class ValidationSeverity(IntEnum):
    """Severity levels for validation issues."""

    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass
class ValidationIssue:
    """Represents a single validation issue.

    Attributes:
        severity: The severity level of the issue
        field: The field name that has the issue
        message: Human-readable description of the issue
        value: The value that caused the issue
        context: Optional context information (e.g., row, freelancer)
    """

    severity: ValidationSeverity
    field: str
    message: str
    value: Any
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """Return string representation of the issue.

        Returns:
            Formatted string with severity, field, and message
        """
        severity_name = self.severity.name
        context_str = ""
        if self.context:
            context_parts = [f"{k}={v}" for k, v in self.context.items()]
            context_str = f" ({', '.join(context_parts)})"

        return f"[{severity_name}] {self.field}: {self.message}{context_str}"


class ValidationReport:
    """Collects and manages validation issues.

    This class accumulates validation errors, warnings, and info messages,
    and provides methods to query, format, and merge validation results.

    Example:
        >>> report = ValidationReport()
        >>> report.add_error("date", "Invalid date", "2023-13-45")
        >>> report.add_warning("break_minutes", "High break time", 400)
        >>> if not report.is_valid():
        ...     print(report.format())
    """

    def __init__(self) -> None:
        """Initialize an empty validation report."""
        self.issues: List[ValidationIssue] = []

    @property
    def error_count(self) -> int:
        """Get the number of errors in the report.

        Returns:
            Count of error-level issues
        """
        return sum(
            1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Get the number of warnings in the report.

        Returns:
            Count of warning-level issues
        """
        return sum(
            1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING
        )

    @property
    def info_count(self) -> int:
        """Get the number of info messages in the report.

        Returns:
            Count of info-level issues
        """
        return sum(
            1 for issue in self.issues if issue.severity == ValidationSeverity.INFO
        )

    def is_valid(self) -> bool:
        """Check if validation passed (no errors).

        Warnings and info messages do not affect validity.

        Returns:
            True if no errors are present, False otherwise
        """
        return self.error_count == 0

    def has_errors(self) -> bool:
        """Check if the report has any errors.

        Returns:
            True if errors are present, False otherwise
        """
        return self.error_count > 0

    def add_error(
        self,
        field: str,
        message: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an error to the report.

        Args:
            field: The field name with the error
            message: Human-readable error description
            value: The value that caused the error
            context: Optional context information
        """
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field=field,
            message=message,
            value=value,
            context=context,
        )
        self.issues.append(issue)

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a warning to the report.

        Args:
            field: The field name with the warning
            message: Human-readable warning description
            value: The value that triggered the warning
            context: Optional context information
        """
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field=field,
            message=message,
            value=value,
            context=context,
        )
        self.issues.append(issue)

    def add_info(
        self,
        field: str,
        message: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an info message to the report.

        Args:
            field: The field name related to the info
            message: Human-readable info description
            value: The value related to the info
            context: Optional context information
        """
        issue = ValidationIssue(
            severity=ValidationSeverity.INFO,
            field=field,
            message=message,
            value=value,
            context=context,
        )
        self.issues.append(issue)

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues.

        Returns:
            List of error issues
        """
        return [
            issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR
        ]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues.

        Returns:
            List of warning issues
        """
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        ]

    def merge(self, other: "ValidationReport") -> None:
        """Merge another validation report into this one.

        Args:
            other: Another ValidationReport to merge
        """
        self.issues.extend(other.issues)

    def summary(self) -> str:
        """Get a summary of the validation report.

        Returns:
            Summary string with counts of errors, warnings, and info messages
        """
        parts = []
        if self.error_count > 0:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count > 0:
            parts.append(f"{self.warning_count} warning(s)")
        if self.info_count > 0:
            parts.append(f"{self.info_count} info message(s)")

        if not parts:
            return "No issues found"

        return ", ".join(parts)

    def format(self) -> str:
        """Format the validation report for display.

        Returns:
            Formatted string with all issues
        """
        if not self.issues:
            return "Validation successful - no issues found"

        lines = [f"Validation Report - {self.summary()}", "=" * 60]

        # Group by severity
        errors = self.get_errors()
        if errors:
            lines.append("\nERRORS:")
            for issue in errors:
                lines.append(f"  - {issue}")

        warnings = self.get_warnings()
        if warnings:
            lines.append("\nWARNINGS:")
            for issue in warnings:
                lines.append(f"  - {issue}")

        info_issues = [
            issue for issue in self.issues if issue.severity == ValidationSeverity.INFO
        ]
        if info_issues:
            lines.append("\nINFO:")
            for issue in info_issues:
                lines.append(f"  - {issue}")

        return "\n".join(lines)
