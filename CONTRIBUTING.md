# Contributing to Billing System

Thank you for your interest in contributing to the Billing System! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Development Workflow](#development-workflow)
5. [Code Standards](#code-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of:
- Experience level
- Gender identity and expression
- Sexual orientation
- Disability
- Personal appearance
- Body size
- Race
- Ethnicity
- Age
- Religion
- Nationality

### Expected Behavior

- Be respectful and inclusive in communications
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Accept responsibility for mistakes and learn from them
- Prioritize what's best for the community and project

### Unacceptable Behavior

- Harassment, discrimination, or exclusionary behavior
- Trolling, insulting comments, or personal attacks
- Publishing others' private information without permission
- Any conduct that would be inappropriate in a professional setting

### Enforcement

Violations of this Code of Conduct may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:
- Python 3.9 or higher
- Git
- A GitHub account
- Basic familiarity with Git workflows
- (Optional) Google Cloud account for integration testing

### First Contributions

Looking for a good first issue? Check for issues labeled:
- `good first issue` - Suitable for new contributors
- `help wanted` - Extra help needed
- `documentation` - Documentation improvements

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/project_billing_system_new.git
cd project_billing_system_new

# Add upstream remote
git remote add upstream https://github.com/HendrikHarren/project_billing_system_new.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your test Google API credentials
# See docs/USER_GUIDE.md for setup instructions
```

### 4. Verify Setup

```bash
# Run tests
pytest

# Run quality checks
pre-commit run --all-files

# Test connection (if configured)
python test_connection.py
```

---

## Development Workflow

### Branch Strategy

- `main` - Stable, production-ready code
- `feature/issue-<number>-<description>` - New features
- `fix/issue-<number>-<description>` - Bug fixes
- `docs/<description>` - Documentation changes

### Creating a Feature Branch

```bash
# Sync with upstream
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/issue-42-new-feature
```

### Test-Driven Development (TDD)

We follow TDD practices:

1. **Write test first** - Define expected behavior
2. **Run test (should fail)** - Red phase
3. **Write minimal code** - Make test pass (Green phase)
4. **Refactor** - Improve code quality
5. **Repeat** - Add edge cases and expand coverage

**Example workflow:**

```bash
# 1. Create test file
touch tests/unit/test_new_feature.py

# 2. Write failing test
# ... edit test_new_feature.py ...

# 3. Run test (should fail)
pytest tests/unit/test_new_feature.py -v

# 4. Implement feature
# ... edit src/new_feature.py ...

# 5. Run test (should pass)
pytest tests/unit/test_new_feature.py -v

# 6. Refactor and verify
pytest tests/unit/test_new_feature.py -v
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Example:**

```
feat(calculators): Add support for overtime billing calculation

Implement overtime rate multiplier for hours exceeding threshold.
Includes validation for overtime rules and edge cases.

Fixes #42
```

---

## Code Standards

### Python Style

We enforce strict code quality standards:

- **Formatter**: [Black](https://github.com/psf/black) (line length: 100)
- **Import Sorter**: [isort](https://pycqa.github.io/isort/)
- **Linter**: [flake8](https://flake8.pycqa.org/) with docstring checks
- **Type Checker**: [mypy](http://mypy-lang.org/) in strict mode
- **Security**: [bandit](https://bandit.readthedocs.io/)

### Code Quality Checklist

Before committing, ensure:

- [ ] Code follows Black formatting
- [ ] Imports are sorted with isort
- [ ] No flake8 violations
- [ ] All functions have type hints
- [ ] All public functions have docstrings (Google style)
- [ ] No mypy type errors
- [ ] No security issues from bandit
- [ ] Tests pass with 90%+ coverage

### Running Quality Checks

```bash
# Automatic (via pre-commit hooks)
git commit -m "Your message"

# Manual
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
bandit -r src/

# All checks
pre-commit run --all-files
```

### Docstring Style

Use [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) docstrings:

```python
def calculate_billable_hours(
    work_duration: Decimal,
    break_duration: Decimal,
    travel_time: Decimal,
    travel_percentage: Decimal,
) -> Decimal:
    """
    Calculate total billable hours including travel time.

    Args:
        work_duration: Total work duration in hours
        break_duration: Break time in hours
        travel_time: Travel time in hours
        travel_percentage: Percentage of travel time that is billable (0-100)

    Returns:
        Total billable hours as Decimal

    Raises:
        ValueError: If any duration is negative or travel_percentage is invalid

    Example:
        >>> calculate_billable_hours(Decimal("8"), Decimal("0.5"), Decimal("1"), Decimal("50"))
        Decimal('8.0')
    """
    # Implementation
```

---

## Testing Guidelines

### Test Organization

```
tests/
├── unit/              # Fast tests with mocked dependencies
│   ├── calculators/
│   ├── readers/
│   ├── validators/
│   └── ...
├── integration/       # Tests with real Google APIs
│   ├── test_end_to_end.py
│   └── ...
└── fixtures/          # Shared test data
```

### Writing Tests

**Unit Test Example:**

```python
import pytest
from decimal import Decimal
from src.calculators.time_calculator import TimeCalculator

class TestTimeCalculator:
    """Tests for TimeCalculator class."""

    def test_calculate_billable_hours_normal_shift(self):
        """Test billable hours calculation for normal shift."""
        calculator = TimeCalculator()

        result = calculator.calculate_billable_hours(
            work_duration=Decimal("8.0"),
            break_duration=Decimal("0.5"),
            travel_time=Decimal("1.0"),
            travel_percentage=Decimal("50.0")
        )

        assert result == Decimal("8.0")

    def test_calculate_billable_hours_invalid_input(self):
        """Test that invalid input raises ValueError."""
        calculator = TimeCalculator()

        with pytest.raises(ValueError):
            calculator.calculate_billable_hours(
                work_duration=Decimal("-1.0"),
                break_duration=Decimal("0.5"),
                travel_time=Decimal("1.0"),
                travel_percentage=Decimal("50.0")
            )
```

### Test Coverage

- **Minimum**: 90% coverage required
- **Target**: 95%+ coverage for new code
- **Critical paths**: 100% coverage for billing calculations

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_test():
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_integration_test():
    pass

@pytest.mark.api  # Requires Google API access
def test_api_integration():
    pass
```

Run specific test categories:

```bash
pytest -m unit           # Unit tests only
pytest -m "not slow"     # Skip slow tests
pytest -m integration    # Integration tests only
```

---

## Documentation

### Documentation Standards

- Update documentation with code changes
- Use Markdown for all documentation
- Include code examples where applicable
- Keep examples working and tested

### Documentation Types

1. **Code Documentation** - Docstrings in code
2. **User Documentation** - `docs/USER_GUIDE.md`
3. **API Documentation** - `docs/ARCHITECTURE.md`
4. **Configuration** - `docs/CONFIGURATION.md`
5. **Troubleshooting** - `docs/TROUBLESHOOTING.md`

### Updating Documentation

When changing features, update:
- [ ] Docstrings in modified code
- [ ] README.md (if feature list changes)
- [ ] docs/ARCHITECTURE.md (if architecture changes)
- [ ] docs/USER_GUIDE.md (if usage changes)
- [ ] docs/CONFIGURATION.md (if config changes)

---

## Pull Request Process

### Before Creating a PR

1. **Sync with upstream**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run full test suite**
   ```bash
   pytest --cov=src
   ```

3. **Run quality checks**
   ```bash
   pre-commit run --all-files
   ```

4. **Update documentation**
   - Update relevant docs
   - Add/update docstrings

### Creating a Pull Request

1. **Push your branch**
   ```bash
   git push origin your-feature-branch
   ```

2. **Create PR on GitHub**
   - Use descriptive title: `feat: Add overtime billing calculation (#42)`
   - Fill out PR template completely
   - Link related issues

3. **PR Template**
   ```markdown
   ## Description
   Brief description of changes

   ## Related Issues
   Fixes #42

   ## Changes Made
   - Added overtime billing calculation
   - Updated project terms reader
   - Added comprehensive tests

   ## Testing
   - [ ] All tests pass
   - [ ] Coverage >= 90%
   - [ ] Manual testing completed

   ## Documentation
   - [ ] README updated
   - [ ] Docstrings added/updated
   - [ ] USER_GUIDE updated (if needed)

   ## Checklist
   - [ ] Code follows project standards
   - [ ] Tests added for new functionality
   - [ ] All CI checks pass
   - [ ] Documentation updated
   ```

### PR Review Process

1. **Automated checks** - CI pipeline must pass
2. **Code review** - At least one approval required
3. **Address feedback** - Make requested changes
4. **Final approval** - Maintainer approves and merges

### After Merge

1. **Delete feature branch**
   ```bash
   git branch -d your-feature-branch
   git push origin --delete your-feature-branch
   ```

2. **Sync with main**
   ```bash
   git checkout main
   git pull upstream main
   ```

---

## Issue Guidelines

### Creating Issues

Use appropriate issue templates:
- **Bug Report**: For reporting bugs
- **Feature Request**: For proposing new features
- **Documentation**: For documentation improvements

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `question` - Further information requested
- `wontfix` - Will not be worked on

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (Python version, OS, etc.)
- Relevant logs or error messages

### Feature Requests

Include:
- Clear description of proposed feature
- Use case and motivation
- Possible implementation approach
- Breaking changes (if any)

---

## Questions?

- Check existing [documentation](docs/)
- Search [issues](https://github.com/HendrikHarren/project_billing_system_new/issues)
- Create a new issue with `question` label

Thank you for contributing! 🎉
