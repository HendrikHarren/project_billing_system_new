# Billing System Documentation

## Overview

Welcome to the Billing System documentation! This is a modern Python application for processing freelancer timesheets from Google Sheets, calculating billing amounts, tracking travel reimbursements, and generating comprehensive reports.

## Documentation Navigation

### 🚀 Getting Started

**New Users Start Here:**

1. [User Guide](USER_GUIDE.md) - Complete setup and usage guide
   - Google API setup walkthrough
   - First report generation
   - Common use cases and workflows

2. [Configuration Reference](CONFIGURATION.md) - Environment variables and settings
   - All configuration options explained
   - Example configurations for different environments
   - Security best practices

3. [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
   - Authentication errors
   - Configuration problems
   - Data validation issues
   - Performance troubleshooting

### 🐳 Deployment

**For Production Deployment:**

4. [Deployment Guide](DEPLOYMENT.md) - Production deployment with Docker
   - Docker and Docker Compose setup
   - Production configuration
   - Monitoring and logging
   - Backup and recovery
   - Scaling considerations

### 🏗️ Technical Documentation

**For Developers and Contributors:**

5. [Architecture Overview](ARCHITECTURE.md) - System design and data flow
   - High-level architecture
   - Component responsibilities
   - Data flow diagrams
   - Key algorithms

6. [Caching Guide](CACHING.md) - Dual-layer caching system
   - Cache architecture
   - Performance optimization
   - Configuration tuning

7. [Automated Workflow](AUTOMATED_WORKFLOW.md) - Code quality and CI/CD
   - Pre-commit hooks
   - CI/CD pipeline
   - Quality standards

### 👥 Contributing

8. [Contributing Guidelines](../CONTRIBUTING.md) - How to contribute
   - Development setup
   - Code standards
   - Testing guidelines
   - Pull request process

## Quick Links

- **Main README**: [../README.md](../README.md)
- **Development Plan**: [../DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md)
- **License**: [../LICENSE](../LICENSE)

## Key Features

- **Automated Timesheet Processing**: Extract data from 30+ freelancer Google Sheets
- **Sophisticated Trip Detection**: Identify consecutive on-site days for travel reimbursement
- **Flexible Billing Calculation**: Support different rates per freelancer-project combination
- **Travel Surcharge Handling**: Additional billing for on-site work
- **Multiple Report Formats**: Detailed timesheets, pivot summaries, and weekly capacity views
- **Data Validation**: Comprehensive validation to ensure accuracy and completeness
- **Docker Deployment**: Containerized deployment for production environments
- **Dual-Layer Caching**: 60-90% reduction in API calls with intelligent caching

## System Requirements

- Python 3.9+
- Google Service Account with Sheets and Drive API access
- Access to freelancer timesheet Google Sheets
- (Optional) Docker for containerized deployment

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/HendrikHarren/project_billing_system_new.git
cd project_billing_system_new

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Google API credentials
# See Configuration section below for details
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run only unit tests
pytest -m unit
```

### 4. Generate Reports

```bash
# Generate monthly billing report (future CLI)
python -m src.cli generate-report --month 2023-06

# Validate timesheet data
python -m src.cli validate --all
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

### Required Google API Settings

```env
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_PRIVATE_KEY_ID=your-private-key-id
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nyour-private-key\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
GOOGLE_SUBJECT_EMAIL=hendrik@harren.com
```

### Required Google Drive/Sheets IDs

```env
TIMESHEET_FOLDER_ID=1GGQdjwFNf0u2-4FqwtkL7sKKx6iwqfVm
PROJECT_TERMS_FILE_ID=14JHBLil55qWyezueHdrsSN5psUqdzjWd7HJaPkmIzY0
MONTHLY_INVOICING_FOLDER_ID=1yerh1sIIM8KebKuy-QSDhnXfr4q88uPE
```

### Optional Settings

```env
ENVIRONMENT=development  # development, testing, production
DEBUG=false
LOG_LEVEL=INFO
BATCH_SIZE=10
MAX_RETRIES=3
RETRY_DELAY=1.0
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture documentation.

## Development

### Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/your-feature`
2. **Write Tests First**: Follow TDD approach
3. **Implement Feature**: Write minimal code to pass tests
4. **Run Quality Checks**: `pre-commit run --all-files`
5. **Commit Changes**: Use conventional commit messages
6. **Create Pull Request**: Ensure CI passes

### Code Quality Standards

- **Test Coverage**: Minimum 90% coverage required
- **Code Formatting**: Black formatter (88 char line length)
- **Import Sorting**: isort with Black profile
- **Linting**: flake8 with docstring checks
- **Type Checking**: mypy for static type analysis
- **Security**: bandit for security issue detection

### Running Quality Checks

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests

# Type check
mypy src

# Security check
bandit -r src/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Testing Strategy

### Test Organization

- `tests/unit/`: Fast unit tests with mocks
- `tests/integration/`: Integration tests with real services
- `tests/fixtures/`: Shared test data and fixtures

### Test Markers

- `@pytest.mark.unit`: Unit tests (fast, no external dependencies)
- `@pytest.mark.integration`: Integration tests (slower, may use APIs)
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.api`: Tests requiring Google API access

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run specific test file
pytest tests/unit/test_config.py

# Run with coverage
pytest --cov=src --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Google service account credentials in `.env`
   - Ensure service account has domain-wide delegation enabled
   - Check that `GOOGLE_SUBJECT_EMAIL` is correct

2. **Permission Errors**
   - Verify service account has access to Google Sheets/Drive
   - Check folder and file IDs are correct
   - Ensure timesheet files are shared with service account

3. **Import Errors**
   - Verify virtual environment is activated
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility (3.9+)

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m src.cli generate-report --month 2023-06
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the development workflow
4. Ensure all tests pass: `pytest`
5. Ensure code quality: `pre-commit run --all-files`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or support, please create an issue in the GitHub repository.
