# Project-Specific Claude Code Configuration

## Project Overview

**Billing System** - A modern Python application for processing freelancer timesheets from Google Sheets, calculating billing amounts, tracking travel reimbursements, and generating comprehensive reports.

- **Language**: Python 3.9+
- **Key Technologies**: pandas, pytest, Google Sheets/Drive APIs, Pydantic
- **Development Approach**: Test-Driven Development (TDD)
- **Current Phase**: Phase 5 - Report Generation

## Project Structure

```
project_billing_system_new/
├── src/
│   ├── config/          # Configuration and settings
│   ├── models/          # Data models (Pydantic)
│   ├── services/        # Google API services
│   ├── readers/         # Data extraction from Sheets
│   ├── validators/      # Data validation layer
│   ├── calculators/     # Business logic (time, billing, trips)
│   ├── aggregators/     # Data aggregation and summarization
│   └── writers/         # Output generation (master timesheet, pivot tables)
├── tests/
│   ├── unit/           # Unit tests (mocked dependencies)
│   └── integration/    # Integration tests (real APIs)
├── docs/               # Documentation
└── .claude/            # Claude Code project-specific commands
```

## Code Quality Standards

### Python Best Practices
- **Formatting**: Black (line length 100)
- **Import Sorting**: isort
- **Linting**: flake8 with docstring checks (Google style)
- **Type Checking**: mypy with strict mode
- **Security**: bandit scanning
- **Pre-commit Hooks**: All checks run automatically on commit

### Testing Requirements
- **Coverage Target**: 90% minimum
- **Test Structure**: Unit tests with mocked dependencies
- **TDD Workflow**: Write test → Red → Green → Refactor
- **Test Command**: `pytest --cov=src` for coverage report
- **Isolation**: Unit tests must not make external API calls

### Documentation Standards
- **Docstrings**: Google style with type annotations
- **Module Docs**: Purpose and key components
- **README**: Keep features list current
- **ARCHITECTURE.md**: Update when adding new layers/components
- **Atomic Updates**: Code + docs in same commit

## Development Workflow

### Branch Strategy
- **Main Branch**: Protected, requires PR approval
- **Feature Branches**: `feature/issue-<number>-<slug>` or `issue-<number>-<slug>`
- **Worktrees**: Use `/create-worktree-and-branch-for-github-issue <number>` command

### GitHub Issue Workflow
1. Use `/solve-github-issue <number>` command for structured workflow
2. Post implementation plan as issue comment (wait for approval)
3. Follow TDD: Tests first, then implementation
4. Link commits to issue: Include `#<issue-number>` in commit messages
5. Create PR with detailed summary and test coverage
6. Merge only after CI passes (all Python versions: 3.9, 3.10, 3.11)
7. Clean up branches after merge (local + remote)

### Commit Standards
- **Format**: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- **Issue Reference**: Always include `(#<issue-number>)` or `(Issue #<number>)`
- **Atomicity**: Code + documentation together
- **Footer**: Add Claude Code attribution for significant features

### Pull Request Requirements
- **Title**: `feat: <description> (#<issue-number>)`
- **Body**: Summary, changes, test coverage, test plan
- **Checks**: All CI/CD checks must pass
- **Merge**: Squash and merge with `--delete-branch` flag
- **Footer**: Include Claude Code attribution

## Key Technical Patterns

### Data Flow Architecture
```
Google Sheets → Readers → Validators → Calculators → Aggregators → Writers → Output
```

### Decimal Precision for Finance
- Use `Decimal` type for all monetary calculations
- Never use `float` for billing amounts or hours
- Import: `from decimal import Decimal`

### Business Logic Layers
1. **Readers**: Extract and normalize data
2. **Validators**: Field-level and business rule validation
3. **Calculators**: Time, billing, trip duration calculations
4. **Aggregators**: Multi-source data consolidation
5. **Writers**: Formatted output generation (in progress)

### Testing Patterns
- **Fixtures**: Use comprehensive fixtures from `tests/unit/fixtures/`
- **Mocking**: Mock all external dependencies (Google APIs)
- **Edge Cases**: Overnight shifts, year boundaries, empty data
- **Parametrize**: Use `@pytest.mark.parametrize` for multiple scenarios

## Google API Integration

### Authentication
- Service account credentials via environment variables
- Never commit credentials or `.env` files
- Use `.env.example` as template

### Required Environment Variables
```
GOOGLE_PROJECT_ID
GOOGLE_PRIVATE_KEY
GOOGLE_CLIENT_EMAIL
TIMESHEET_FOLDER_ID
PROJECT_TERMS_FILE_ID
MONTHLY_INVOICING_FOLDER_ID
```

### Optional Cache Configuration
```
ENABLE_SHEETS_CACHE=True          # Enable dual-layer caching (default: True)
CACHE_FILE_PATH=.cache/sheets_cache.json  # Cache file location
CACHE_MAX_SIZE=100                 # Maximum cache entries (default: 100)
CACHE_AUTO_SAVE=True               # Auto-save to disk (default: True)
```

### API Best Practices
- Retry logic with exponential backoff
- Rate limiting handling
- Connection pooling
- Mock-friendly service interfaces

## Common Operations

### Running Tests
```bash
# All tests with coverage
pytest --cov=src

# Unit tests only (fast)
pytest tests/unit/

# Integration tests (requires API access)
pytest tests/integration/

# Specific test file
pytest tests/unit/services/test_google_drive_service.py -v
```

### Code Quality Checks
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Individual checks
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
bandit -r src/
```

### Development Commands
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Test connection
python test_connection.py
```

## Current Implementation Status

### Completed (✅)
- **Phase 1**: Project setup, Google API services, data models
- **Phase 2**: Timesheet reader, project terms reader, data validation
- **Phase 3**: Time calculator, trip calculator, billing calculator
- **Phase 4**: Timesheet aggregator, trip aggregator, weekly hours calculator
- **Phase 5**: Report generation
  - Issue #13: Master timesheet generator (completed 2025-10-05)
  - Issue #14: Pivot table builder (completed 2025-10-05, implemented as native pivot tables)
  - Issue #15: Google Sheets writer (completed 2025-10-05)
- **Performance Optimization**:
  - Issue #41: Dual-layer caching with modification-time-based invalidation (completed 2025-10-05)

### Recently Completed (✅)
- **Caching System** (Issue #41)
  - Dual-layer caching (memory + disk) for Google Sheets data
  - Modification-time-based cache invalidation
  - 60-90% reduction in API calls for unchanged files
  - Persistent across application restarts
  - Thread-safe with LRU eviction
  - 91% test coverage
  - See [docs/CACHING.md](docs/CACHING.md) for details


### Key Algorithms Implemented
- **Overnight Shift Handling**: Correct time calculation across midnight
- **Trip Detection**: Consecutive on-site day grouping
- **Billing Calculation**: Hours × Rate + Travel Surcharge - Costs
- **Weekly Aggregation**: ISO 8601 week numbering with year boundaries

## Critical Rules for Claude Code

### Documentation Synchronization
**ALWAYS** update documentation when modifying:
- Feature implementation → Update README.md features list
- New layer/component → Update docs/ARCHITECTURE.md
- API changes → Update relevant docstrings
- Configuration → Update .env.example

**Verification Process**:
1. Use Grep to find all mentions of changed component
2. Update ALL relevant documentation files
3. Include docs in the same commit as code changes

### Test Coverage Enforcement
- Never mark issue complete without ≥90% coverage
- Run full test suite before creating PR
- Add tests for edge cases (empty data, overnight, year boundaries)
- Verify all Python versions pass (3.9, 3.10, 3.11)

### Atomic Commits
- Code + docs together: `git add src/ docs/ README.md`
- Format: `feat: Implement [feature] with documentation updates`
- Never separate code and documentation commits

### Branch Cleanup
- After PR merge: Delete local AND remote branches
- Use `gh pr merge <number> --squash --delete-branch`
- Verify: `git branch -a` should only show main + active work

## Project-Specific Conventions

### Naming Conventions
- **Classes**: PascalCase (e.g., `TimesheetReader`, `BillingCalculator`)
- **Functions**: snake_case (e.g., `calculate_billable_hours`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_CACHE_TTL`)
- **Test Files**: `test_<module_name>.py`
- **Test Functions**: `test_<function>_<scenario>`

### File Organization
- One class per file (exceptions: related data classes)
- `__init__.py` exports public API
- Private helpers start with underscore
- Tests mirror source structure

### Error Handling
- Use custom exceptions for business logic errors
- Log errors with context (freelancer name, date, project)
- Graceful degradation: Continue processing other entries on error
- Validation issues use `ValidationReport` with severity levels

## Integration with Global Commands

This project uses these global Claude Code commands:
- `/create-worktree-and-branch-for-github-issue <number>` - Create isolated worktree
- `/solve-github-issue <number>` - Structured issue resolution workflow
- `/create-github-issue <description>` - Create well-formatted issues

**Note**: These commands automatically copy `.env`, `.claude/`, `.vscode/`, and `CLAUDE.md` to new worktrees.

## Resources

- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Development Plan**: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)
- **Caching Guide**: [docs/CACHING.md](docs/CACHING.md)
- **Automated Workflow**: [docs/AUTOMATED_WORKFLOW.md](docs/AUTOMATED_WORKFLOW.md)
- **Setup Guide**: [docs/README.md](docs/README.md)
- **GitHub Issues**: Track development progress by phase

---

**Last Updated**: 2025-10-05 (Phase 5 complete, Caching optimization implemented)
