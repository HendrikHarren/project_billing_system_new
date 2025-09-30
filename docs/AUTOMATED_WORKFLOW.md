# Automated Code Quality Workflow

This document explains how the automated code optimization and quality enforcement works in this project.

## Overview

The project uses a multi-layered approach to automatically enforce code quality and optimize code before it reaches the main branch:

1. **Pre-commit Hooks** - Automatic local optimization
2. **CI Pipeline** - Remote validation and enforcement
3. **Branch Protection** - Automatic enforcement of CI results
4. **GitHub Integration** - Prevents problematic code from being merged

## 1. Pre-commit Hooks

### What They Do
Pre-commit hooks automatically run before each commit to optimize and validate your code locally.

### Automatically Applied Fixes
- **Black formatting** - Consistent Python code style
- **isort import sorting** - Organized imports with black compatibility
- **Trailing whitespace removal** - Clean file endings
- **End-of-file newlines** - Proper file formatting
- **YAML/JSON validation** - Syntax checking for config files

### How It Works
```bash
# Installed once per repository
pre-commit install

# Runs automatically on every commit
git commit -m "Your changes"
# → Pre-commit hooks run and auto-fix issues
# → If fixes were applied, commit is aborted
# → Re-run commit to proceed with fixed code
```

### Manual Execution
```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black
```

## 2. CI Pipeline

### Three-Layer Validation
The CI pipeline runs three parallel jobs on every push:

#### **test** (Matrix: Python 3.9, 3.10, 3.11)
- Lint with flake8 (syntax errors only)
- Format check with black
- Import sorting check with isort
- Type checking with mypy
- Full test suite with pytest
- Coverage reporting

#### **lint-and-format**
- Comprehensive black formatting check
- Full flake8 linting
- Import sorting validation
- Type checking

#### **security**
- Dependency vulnerability scanning (safety)
- Security issue detection (bandit)

### Automatic Configuration Sync
All tools use consistent configuration:
- `--profile=black` for isort compatibility
- `--max-line-length=88` for consistent line length
- `--extend-ignore=E203,W503,E231` for black compatibility

## 3. Branch Protection Rules

### Enforcement Policies
The main branch is protected with the following rules:

✅ **Required Status Checks**
- All CI jobs must pass: `lint-and-format`, `security`, `test (3.9)`, `test (3.10)`, `test (3.11)`
- Branches must be up-to-date before merging

✅ **Admin Enforcement**
- Rules apply to all users, including administrators

✅ **Force Push Prevention**
- Direct force pushes to main are blocked
- History preservation is enforced

### What This Means
- **No broken code** can be merged to main
- **All formatting standards** are automatically enforced
- **Security issues** are caught before deployment
- **Test coverage** is maintained

## 4. Developer Workflow

### For New Contributors

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd project_billing_system_new
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   pre-commit install
   ```

2. **Make changes**:
   ```bash
   # Edit code normally
   # Pre-commit hooks will auto-format on commit
   git add .
   git commit -m "Description of changes"
   ```

3. **Push and create PR**:
   ```bash
   git push origin feature-branch
   # Create PR - CI must pass before merge
   ```

### For Regular Development

The workflow is **completely transparent**:
- Write code normally
- Commit as usual - formatting happens automatically
- Push to GitHub - CI validates everything
- Merge when green - branch protection enforces quality

## 5. What Gets Automatically Fixed

### ✅ Automatically Fixed (Pre-commit)
- Code formatting (Black)
- Import organization (isort)
- Trailing whitespace
- Missing end-of-file newlines
- Basic file formatting

### ⚠️ Requires Manual Fix (CI Validation)
- Syntax errors (flake8)
- Type errors (mypy)
- Test failures (pytest)
- Security vulnerabilities (bandit/safety)
- Complex code style issues

### 🚫 Blocked at Merge (Branch Protection)
- Any CI failure
- Outdated branches
- Failed status checks

## 6. Benefits

### For Developers
- **No manual formatting** - tools handle it automatically
- **Consistent code style** - no debates about formatting
- **Early error detection** - catch issues before review
- **Faster reviews** - focus on logic, not style

### For the Project
- **Maintainable codebase** - consistent style and quality
- **Reliable CI/CD** - automated quality gates
- **Security assurance** - automatic vulnerability detection
- **High test coverage** - enforced through CI

## 7. Troubleshooting

### Pre-commit Hook Failures
```bash
# Hook failed and made changes
git add .
git commit  # Retry commit with fixes

# Skip hooks temporarily (not recommended)
git commit --no-verify -m "Emergency fix"

# Update hook versions
pre-commit autoupdate
```

### CI Failures
- **Black/isort failures**: Usually auto-fixed by pre-commit
- **flake8 failures**: Fix syntax/style issues manually
- **Test failures**: Fix failing tests
- **Security issues**: Address vulnerabilities in dependencies

### Branch Protection Issues
- **Status checks pending**: Wait for CI to complete
- **Branch not up-to-date**: Pull latest changes and rebase
- **Required reviews**: Request code review from team member

## 8. Configuration Files

### Pre-commit Configuration
`.pre-commit-config.yaml` - Defines local hooks and their settings

### CI Pipeline Configuration
`.github/workflows/ci.yml` - Defines remote validation jobs

### Python Tool Configuration
- `pytest.ini` - Test configuration
- `requirements-dev.txt` - Development dependencies
- Various tool args in pre-commit and CI configs

This automated workflow ensures code quality without developer overhead, making the codebase maintainable and reliable.
