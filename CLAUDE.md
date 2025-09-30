# Project Billing System - Claude Code Configuration

## Project Overview
Modern Python billing system for processing freelancer timesheets from Google Sheets, with automated calculation of billing amounts, travel reimbursements, and comprehensive reporting.

**Current Status**: Google API service layer complete ✅ | Issue #2 complete | Next: Data models and validation (Issue #3)

## Development Standards & Automated Workflow

### Code Quality Automation
This project uses **automated code optimization and quality enforcement**:

- 🔧 **Pre-commit hooks** - Auto-format code before every commit (Black, isort, trailing whitespace)
- 🛡️ **Branch protection** - CI pipeline must pass before merging to main
- ✅ **CI/CD integration** - Automatic validation on every push (lint, format, security, tests)
- 📋 **Quality gates** - flake8, mypy, bandit, pytest enforcement

**IMPORTANT**: Follow the automated workflow:
1. All commits trigger pre-commit hooks for automatic formatting
2. Changes to main branch MUST go through Pull Request process
3. All CI checks must pass before merge (branch protection enforced)
4. Never use `--no-verify` to bypass pre-commit hooks unless emergency

### Development Environment Setup
```bash
# Required setup for development
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install  # CRITICAL: Enables automatic code formatting
```

### Testing & Quality Standards
- **90% test coverage minimum** (enforced via CI)
- **pytest** for all testing with comprehensive mocking patterns
- **No external API calls** in unit tests (use proper mocks)
- **TDD approach** where applicable (Red-Green-Refactor)

## Technical Architecture

### Core Technologies
- **Python 3.9+** with modern async/await patterns
- **Google APIs**: Sheets v4, Drive v3 with Application Default Credentials
- **Pandas** for data processing with native DataFrame integration
- **Pydantic v2** with pydantic-settings for configuration management
- **pytest** with comprehensive fixtures and mocking

### Service Layer Patterns
- **Retry handler** with exponential backoff, jitter, and circuit breaker
- **Google API services** with proper authentication and error handling
- **Configuration management** with environment variable validation
- **Comprehensive logging** with structured output

### Key Components Completed ✅
1. **Google Drive Service** (`src/services/google_drive_service.py`)
   - File listing, metadata retrieval, search functionality
   - Timesheet file discovery with date filtering
   - Comprehensive error handling and retry logic

2. **Google Sheets Service** (`src/services/google_sheets_service.py`)
   - Native pandas DataFrame support for reading/writing
   - Batch operations for performance optimization
   - Sheet metadata management and creation

3. **Retry Handler** (`src/services/retry_handler.py`)
   - Exponential backoff with cryptographically secure jitter
   - Circuit breaker pattern for failure management
   - Comprehensive statistics tracking

4. **Configuration System** (`src/config/settings.py`)
   - Pydantic v2 validation with environment variables
   - Google service account credential management
   - Environment-specific settings (development/testing/production)

## Development Workflow Integration

### Making Changes
```bash
# Standard workflow - automation handles quality
git checkout -b feature/description
# Make changes...
git add .
git commit -m "Clear description"  # Pre-commit hooks run automatically
git push origin feature/description
# Create PR - CI must pass before merge
```

### Branch Management
- **main**: Protected branch, requires PR + CI passing
- **feature/***: Feature development branches
- **fix/***: Bug fix branches
- **develop**: Integration branch (if using GitFlow)

### Commit Standards
- Use conventional commit format: `type(scope): description`
- Include issue references: `Fixes #23` or `Relates to #23`
- Let pre-commit hooks handle formatting
- Include co-author attribution for Claude assistance:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

## File Structure & Patterns

### Source Code Organization
```
src/
├── config/          # Configuration management
├── services/        # Google API services with retry logic
├── calculators/     # Business logic (TO IMPLEMENT)
├── aggregators/     # Data aggregation (TO IMPLEMENT)
├── models/          # Data models (TO IMPLEMENT)
└── cli/            # Command-line interface (TO IMPLEMENT)
```

### Test Organization
```
tests/
├── unit/           # Isolated unit tests with mocks
├── integration/    # API integration tests (requires credentials)
└── fixtures/       # Shared test data and utilities
```

### Key Files
- `.pre-commit-config.yaml` - Automated code quality hooks
- `.github/workflows/ci.yml` - CI/CD pipeline configuration
- `pytest.ini` - Test configuration
- `requirements-dev.txt` - Development dependencies
- `conftest.py` - Shared pytest fixtures

## Development Practices

### Code Style (Automated)
- **Black** formatting (line length 88)
- **isort** import sorting with black profile
- **Type hints** required for all functions
- **Docstrings** for all public functions and classes

### Testing Patterns
- **Comprehensive mocking** for external services
- **Fixture-based setup** with proper cleanup
- **Error scenario testing** for robust error handling
- **Integration tests** marked and skipped without credentials

### Error Handling
- **Structured exceptions** with clear error messages
- **Retry patterns** for transient failures
- **Circuit breakers** for persistent failures
- **Comprehensive logging** for debugging

## Issue Tracking & Development Phases

### Current Phase: Foundation ✅
- [x] Issue #1: Project Setup & Configuration
- [x] Issue #2: Google API Service Layer
- [ ] Issue #3: Data Models & Validation (NEXT)

### Upcoming Phases
- **Phase 2**: Data Collection (Issues #4-6)
- **Phase 3**: Business Logic (Issues #7-9)
- **Phase 4**: Data Aggregation (Issues #10-12)
- **Phase 5**: Report Generation (Issues #13-15)
- **Phase 6**: CLI Application (Issues #16-18)
- **Phase 7**: Documentation & Testing (Issues #19-20)

## Documentation Standards

### Required Documentation
- **README.md** - Project overview and quick start
- **docs/ARCHITECTURE.md** - System design and data flow
- **docs/AUTOMATED_WORKFLOW.md** - Development workflow automation
- **Inline docstrings** - All public APIs documented
- **Type annotations** - Full type coverage

### Documentation Synchronization
When modifying code, config, or architecture:
1. **ALWAYS update documentation immediately**
2. **Search for ALL references** to changed components
3. **Update examples and usage patterns**
4. **Verify documentation matches working code**

## Critical Reminders

### Automated Workflow Compliance
- ✅ **Use pre-commit hooks** - Never bypass with `--no-verify`
- ✅ **Follow branch protection** - Changes to main via PR only
- ✅ **Respect CI requirements** - All checks must pass
- ✅ **Maintain test coverage** - 90% minimum coverage

### Issue Management
- **Link commits to issues** using `Fixes #N` or `Relates to #N`
- **Update issue status** when making progress
- **Document implementation plans** in issue comments
- **Close issues only when fully complete** with high test coverage

### Security & Best Practices
- **Never commit secrets** or API keys
- **Use environment variables** for all configuration
- **Follow least privilege** for API permissions
- **Regular dependency updates** for security

This configuration ensures Claude follows the project's automated workflow and maintains the high quality standards established for the billing system.
