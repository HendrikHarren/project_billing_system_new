# Billing System

A modern Python application for processing freelancer timesheets from Google Sheets, calculating billing amounts, tracking travel reimbursements, and generating comprehensive reports.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Google Service Account with Sheets and Drive API access
- Access to freelancer timesheet Google Sheets

### Installation

```bash
# Clone the repository
git clone https://github.com/HendrikHarren/project_billing_system_new.git
cd project_billing_system_new

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Google API credentials
```

Required environment variables:
- `GOOGLE_PROJECT_ID`: Your Google Cloud project ID
- `GOOGLE_PRIVATE_KEY`: Service account private key
- `GOOGLE_CLIENT_EMAIL`: Service account email
- `TIMESHEET_FOLDER_ID`: Google Drive folder containing timesheets
- `PROJECT_TERMS_FILE_ID`: Google Sheets file with project rates
- `MONTHLY_INVOICING_FOLDER_ID`: Output folder for generated reports

See `.env.example` for complete configuration options.

### Basic Usage

```bash
# Test Google API connection
python test_connection.py

# Run tests
pytest

#CLI Commands

# Generate monthly billing report
python -m src.cli generate-report --month 2024-10

# Generate report with filters
python -m src.cli generate-report --month 2024-10 --project PROJ001
python -m src.cli generate-report --month 2024-10 --freelancer "John Doe"

# List available timesheets
python -m src.cli list-timesheets

# Validate timesheet data quality
python -m src.cli validate-data
python -m src.cli validate-data --month 2024-10
python -m src.cli validate-data --file-id abc123xyz --severity warning

# Get help for any command
python -m src.cli --help
python -m src.cli generate-report --help
```

## 🏗️ Architecture

The system transforms raw timesheet data through several processing layers:

1. **Data Collection**: Extract from Google Sheets with validation
2. **Business Logic**: Calculate hours, detect trips, apply billing rules
3. **Aggregation**: Combine data from multiple freelancers
4. **Output Generation**: Create formatted reports with pivot tables

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## 🧪 Development

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (automatic code formatting)
pre-commit install

# Run quality checks
pre-commit run --all-files
```

### Automated Code Quality

This project features **automatic code optimization and quality enforcement**:

- 🔧 **Pre-commit hooks** - Auto-format code before every commit
- 🛡️ **Branch protection** - CI pipeline must pass before merging
- ✅ **CI/CD integration** - Automatic validation on every push
- 📋 **Consistent standards** - Black, isort, flake8, mypy enforcement

See [Automated Workflow Guide](docs/AUTOMATED_WORKFLOW.md) for complete details.

### Running Tests

```bash
# All tests with coverage
pytest --cov=src

# Unit tests only (isolated, no external dependencies)
pytest tests/unit/

# Integration tests (requires API access)
pytest tests/integration/

# Smoke tests (quick verification)
pytest tests/unit/services/test_services_smoke.py

# Run specific test file
pytest tests/unit/services/test_google_drive_service.py -v
```

#### Test Architecture

- **Unit Tests**: Fully mocked, no external API calls
- **Integration Tests**: Require real Google API credentials
- **Service Tests**: Use proper mocking patterns with patch cleanup
- **Configuration Tests**: Environment variable isolation

All unit tests use proper mocking to ensure fast, isolated execution without external dependencies.

### Code Quality

The project enforces high code quality standards:
- **90% test coverage** minimum
- **Black** code formatting
- **flake8** linting with docstring checks
- **mypy** static type checking
- **isort** import sorting
- **bandit** security scanning

## 📊 Features

### Current Capabilities
- ✅ Google API connection and authentication
- ✅ Configuration management with validation
- ✅ Modern service layer with retry logic and circuit breaker
- ✅ Exponential backoff with jitter for rate limiting
- ✅ **Dual-layer caching with modification-time-based invalidation**
  - 60-90% reduction in Google API calls for unchanged files
  - Persistent disk cache across application restarts
  - Fast in-memory cache during session
  - Automatic invalidation when files are modified
- ✅ Test framework with comprehensive fixtures
- ✅ CI/CD pipeline with quality checks
- ✅ Timesheet data reading and validation (TimesheetReader)
- ✅ Project terms reading with caching (ProjectTermsReader)
- ✅ Comprehensive data validation layer with business rules
- ✅ Time calculation engine with billable hours and travel surcharge
- ✅ Trip duration calculator (consecutive on-site days grouping)
- ✅ Billing calculator with comprehensive financial metrics
- ✅ Timesheet aggregator for multi-source data consolidation
- ✅ Trip reimbursement aggregator with duration-based calculation
- ✅ Weekly hours calculator for capacity and utilization reports
- ✅ Master timesheet generation with 4 output sheets:
  - Timesheet_master & Trips_master: Static data with formatting
  - Pivot_master & Weekly_reporting: Native Google Sheets pivot tables
- ✅ CLI interface with 3 commands:
  - `generate-report`: Full end-to-end report generation
  - `list-timesheets`: List available timesheets from Google Drive
  - `validate-data`: Validate data quality with detailed reporting

### Planned Features (Development Roadmap)
- 🚧 Automated scheduling and monitoring
- 🚧 Error handling & logging enhancements

## 📈 Project Status

**Phase 1: Foundation** ✅ Complete
- [x] Project setup and configuration (Issue #1)
- [x] Google API service layer (Issue #2)
- [x] Data models and validation (Issue #3)

**Phase 2: Data Collection** ✅ Complete
- [x] Timesheet reader implementation (Issue #4)
- [x] Project terms reader with caching (Issue #5)
- [x] Data validation layer (Issue #6)

**Phase 3: Business Logic** ✅ Complete
- [x] Time calculation engine (Issue #7)
- [x] Trip duration calculator (Issue #8)
- [x] Billing calculator (Issue #9)

**Phase 4: Data Aggregation** ✅ Complete
- [x] Timesheet aggregator (Issue #10)
- [x] Trip reimbursement calculator (Issue #11)
- [x] Weekly hours calculator (Issue #12)

**Phase 5: Report Generation** ✅ Complete
- [x] Master timesheet generator (Issue #13)
- [x] Pivot table builder (Issue #14)
- [x] Google Sheets writer (Issue #15)

**Phase 6: CLI Application** 🚧 In Progress
- [x] CLI Interface (Issue #16)
- [ ] Report Automation (Issue #17)
- [ ] Error Handling & Logging (Issue #18)

**Phase 7**: See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for complete roadmap

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following TDD practices
4. Ensure all tests pass: `pytest`
5. Run quality checks: `pre-commit run --all-files`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📋 GitHub Issues

Development is tracked through GitHub issues organized by phases:
- **Issues #1-3**: Foundation (Project setup, API layer, data models)
- **Issues #4-6**: Data collection (Readers and validation)
- **Issues #7-9**: Core business logic (Calculations)
- **Issues #10-12**: Data aggregation
- **Issues #13-15**: Report generation
- **Issues #16-18**: CLI application
- **Issues #19-20**: Testing and documentation

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and data flow
- [Development Plan](DEVELOPMENT_PLAN.md) - Complete project roadmap
- [Setup Guide](docs/README.md) - Detailed setup and usage instructions
- [Automated Workflow](docs/AUTOMATED_WORKFLOW.md) - Code quality and CI/CD automation

## 🛠️ Tech Stack

- **Language**: Python 3.9+
- **Data Processing**: Pandas
- **API Integration**: Google Sheets/Drive APIs
- **Configuration**: Pydantic with environment variables
- **Testing**: pytest with comprehensive fixtures
- **Quality**: Black, flake8, mypy, isort, bandit
- **CI/CD**: GitHub Actions
- **Documentation**: Markdown with architecture diagrams

## 📞 Support

For questions or support:
1. Check the [documentation](docs/)
2. Search existing [GitHub issues](https://github.com/HendrikHarren/project_billing_system_new/issues)
3. Create a new issue with detailed information

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Current Status**: Phase 4 complete ✅ | Phase 5 Report Generation in progress 🚧 (Issues #13, #14, #15 complete)
