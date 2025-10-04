"""Tests for validation report functionality."""

from src.validators.validation_report import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        assert ValidationSeverity.ERROR
        assert ValidationSeverity.WARNING
        assert ValidationSeverity.INFO

    def test_severity_order(self):
        """Test that severity levels can be compared."""
        assert ValidationSeverity.ERROR.value > ValidationSeverity.WARNING.value
        assert ValidationSeverity.WARNING.value > ValidationSeverity.INFO.value


class TestValidationIssue:
    """Tests for ValidationIssue data class."""

    def test_create_error_issue(self):
        """Test creating an error validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field="date",
            message="Invalid date format",
            value="2023-13-45",
            context={"row": 5},
        )

        assert issue.severity == ValidationSeverity.ERROR
        assert issue.field == "date"
        assert issue.message == "Invalid date format"
        assert issue.value == "2023-13-45"
        assert issue.context == {"row": 5}

    def test_create_warning_issue(self):
        """Test creating a warning validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field="break_minutes",
            message="Break time is unusually high",
            value=480,
        )

        assert issue.severity == ValidationSeverity.WARNING
        assert issue.field == "break_minutes"
        assert issue.value == 480

    def test_issue_without_context(self):
        """Test creating issue without context."""
        issue = ValidationIssue(
            severity=ValidationSeverity.INFO,
            field="notes",
            message="Notes field is empty",
            value=None,
        )

        assert issue.context is None

    def test_issue_string_representation(self):
        """Test string representation of validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field="start_time",
            message="Invalid time format",
            value="25:00",
        )

        str_repr = str(issue)
        assert "ERROR" in str_repr
        assert "start_time" in str_repr
        assert "Invalid time format" in str_repr


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_create_empty_report(self):
        """Test creating an empty validation report."""
        report = ValidationReport()

        assert report.is_valid()
        assert report.error_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0
        assert len(report.issues) == 0

    def test_add_error(self):
        """Test adding an error to the report."""
        report = ValidationReport()
        report.add_error("date", "Invalid date", "invalid-date")

        assert not report.is_valid()
        assert report.error_count == 1
        assert report.warning_count == 0
        assert len(report.issues) == 1
        assert report.issues[0].severity == ValidationSeverity.ERROR

    def test_add_warning(self):
        """Test adding a warning to the report."""
        report = ValidationReport()
        report.add_warning("break_minutes", "High break time", 300)

        assert report.is_valid()  # Warnings don't make report invalid
        assert report.error_count == 0
        assert report.warning_count == 1
        assert len(report.issues) == 1

    def test_add_info(self):
        """Test adding info message to the report."""
        report = ValidationReport()
        report.add_info("notes", "Notes field is empty", None)

        assert report.is_valid()
        assert report.info_count == 1
        assert len(report.issues) == 1

    def test_add_multiple_issues(self):
        """Test adding multiple issues to the report."""
        report = ValidationReport()
        report.add_error("date", "Invalid date", "2023-13-45")
        report.add_error("start_time", "Invalid time", "25:00")
        report.add_warning("break_minutes", "High break", 400)
        report.add_info("notes", "Empty notes", None)

        assert not report.is_valid()
        assert report.error_count == 2
        assert report.warning_count == 1
        assert report.info_count == 1
        assert len(report.issues) == 4

    def test_get_errors_only(self):
        """Test filtering to get only errors."""
        report = ValidationReport()
        report.add_error("date", "Invalid date", "2023-13-45")
        report.add_warning("break_minutes", "High break", 400)
        report.add_error("start_time", "Invalid time", "25:00")

        errors = report.get_errors()

        assert len(errors) == 2
        assert all(issue.severity == ValidationSeverity.ERROR for issue in errors)

    def test_get_warnings_only(self):
        """Test filtering to get only warnings."""
        report = ValidationReport()
        report.add_error("date", "Invalid date", "2023-13-45")
        report.add_warning("break_minutes", "High break", 400)
        report.add_warning("travel_time", "High travel", 300)

        warnings = report.get_warnings()

        assert len(warnings) == 2
        assert all(issue.severity == ValidationSeverity.WARNING for issue in warnings)

    def test_merge_reports(self):
        """Test merging two validation reports."""
        report1 = ValidationReport()
        report1.add_error("date", "Invalid date", "2023-13-45")
        report1.add_warning("break_minutes", "High break", 400)

        report2 = ValidationReport()
        report2.add_error("start_time", "Invalid time", "25:00")
        report2.add_info("notes", "Empty notes", None)

        report1.merge(report2)

        assert report1.error_count == 2
        assert report1.warning_count == 1
        assert report1.info_count == 1
        assert len(report1.issues) == 4

    def test_format_report_empty(self):
        """Test formatting an empty report."""
        report = ValidationReport()
        formatted = report.format()

        assert "Validation successful" in formatted or "No issues" in formatted

    def test_format_report_with_errors(self):
        """Test formatting a report with errors."""
        report = ValidationReport()
        report.add_error("date", "Invalid date format", "2023-13-45", {"row": 5})
        report.add_warning("break_minutes", "High break time", 400, {"row": 5})

        formatted = report.format()

        assert "ERROR" in formatted
        assert "WARNING" in formatted
        assert "date" in formatted
        assert "Invalid date format" in formatted
        assert "row" in formatted.lower()

    def test_add_issue_with_context(self):
        """Test adding issue with context information."""
        report = ValidationReport()
        report.add_error(
            field="project_code",
            message="Project not found",
            value="INVALID-PROJECT",
            context={"row": 10, "freelancer": "John Doe"},
        )

        assert report.issues[0].context["row"] == 10
        assert report.issues[0].context["freelancer"] == "John Doe"

    def test_has_errors(self):
        """Test has_errors method."""
        report = ValidationReport()
        assert not report.has_errors()

        report.add_warning("field", "warning", None)
        assert not report.has_errors()

        report.add_error("field", "error", None)
        assert report.has_errors()

    def test_summary(self):
        """Test getting summary statistics."""
        report = ValidationReport()
        report.add_error("field1", "error1", None)
        report.add_error("field2", "error2", None)
        report.add_warning("field3", "warning1", None)

        summary = report.summary()

        assert "2" in summary  # 2 errors
        assert "1" in summary  # 1 warning
        assert "error" in summary.lower()
        assert "warning" in summary.lower()
