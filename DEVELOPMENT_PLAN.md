# Billing System Development Plan

## Project Overview

Transform the existing Jupyter notebook-based billing system into a modern Python application using Test-Driven Development (TDD). The system processes freelancer timesheets from Google Sheets, calculates billing amounts, tracks travel reimbursements, and generates comprehensive reports.

## System Architecture

```
Input: Individual Google Sheets timesheets (30+ freelancers)
    ↓
Processing: Python application with business logic
    ↓
Output: Master timesheet with 4 sheets (Timesheet, Trips, Pivot, Weekly)
```

## Key Business Requirements

- **Trip Duration Calculation**: Detect consecutive on-site days for travel reimbursement
- **Flexible Billing**: Different rates per freelancer-project combination
- **Travel Surcharges**: Additional billing for on-site work
- **Multiple Report Views**: Detailed, summary, and weekly capacity views
- **Data Validation**: Ensure accuracy and completeness

## Development Methodology

### TDD Approach
1. **Red**: Write failing test defining expected behavior
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Improve code quality while maintaining functionality
4. **Repeat**: Add edge cases and expand coverage

### Small Step Strategy
- Each work package is independently testable
- Maximum 1-2 days per issue
- Frequent commits with working code
- Early feedback on core algorithms

---

## Phase 1: Foundation (Week 1)

### Issue #1: Project Setup & Configuration
**Goal**: Establish robust development environment and configuration management

**Tasks**:
- Set up project structure (src/, tests/, docs/, config/)
- Configure pytest with fixtures, coverage reporting
- Create configuration management using environment variables
- Set up GitHub Actions for CI/CD
- Create development and testing requirements files

**Acceptance Criteria**:
- [ ] Tests run with `pytest` and show coverage
- [ ] Configuration loads from environment variables
- [ ] CI pipeline runs on GitHub pushes
- [ ] Development dependencies clearly documented

**Test Strategy**: Infrastructure tests, configuration loading tests

---

### Issue #2: Google API Service Layer
**Goal**: Create reliable, testable Google API interfaces

**Tasks**:
- Implement GoogleSheetsService with connection pooling
- Implement GoogleDriveService for file operations
- Add retry logic for API rate limiting
- Create comprehensive error handling
- Write integration tests with mock responses

**Acceptance Criteria**:
- [ ] Services handle authentication and reconnection
- [ ] Retry logic works for rate limits and temporary failures
- [ ] Mock tests verify API call patterns
- [ ] Real API tests can be run against test environment

**Test Strategy**: Unit tests with mocks, integration tests with real API

---

### Issue #3: Data Models
**Goal**: Define type-safe data structures for all business entities

**Tasks**:
- Create Timesheet dataclass with validation
- Create Project and ProjectTerms dataclasses
- Create TripReimbursement and Trip dataclasses
- Add validation methods and error handling
- Write comprehensive unit tests

**Acceptance Criteria**:
- [ ] All models have type hints and validation
- [ ] Invalid data raises appropriate exceptions
- [ ] Models can serialize/deserialize from Google Sheets format
- [ ] 100% test coverage on validation logic

**Test Strategy**: Property-based testing, edge case validation

---

## Phase 2: Data Collection (Week 2)

### Issue #4: Timesheet Reader
**Goal**: Reliably extract and parse timesheet data from Google Sheets

**Tasks**:
- Implement TimesheetReader class
- Handle various date/time formats
- Parse project codes and location data
- Manage missing or malformed data
- Extract freelancer name from sheet title

**Acceptance Criteria**:
- [ ] Reads all columns correctly with proper types
- [ ] Handles empty rows and missing data gracefully
- [ ] Parses dates and times consistently
- [ ] Validates project codes against known values

**Test Strategy**: Test with real timesheet samples, edge case handling

---

### Issue #5: Project Terms Reader
**Goal**: Load and cache project-specific billing terms

**Tasks**:
- Implement ProjectTermsReader for main terms sheet
- Read trip reimbursement terms
- Create caching mechanism for performance
- Validate terms data completeness
- Handle missing or invalid terms

**Acceptance Criteria**:
- [ ] Loads main terms (rates, costs, travel rules) correctly
- [ ] Loads trip terms (duration, reimbursement) correctly
- [ ] Caches data to minimize API calls
- [ ] Validates required fields exist

**Test Strategy**: Mock terms data, cache invalidation tests

---

### Issue #6: Data Validation Layer
**Goal**: Ensure data quality and business rule compliance

**Tasks**:
- Create validators for dates, times, project codes
- Implement business rule validation (break < work time, etc.)
- Create validation report generator
- Handle validation errors gracefully

**Acceptance Criteria**:
- [ ] Validates all timesheet fields with clear error messages
- [ ] Checks business rules (logical time ranges, valid projects)
- [ ] Generates detailed validation reports
- [ ] Allows partial validation for different scenarios

**Test Strategy**: Invalid data scenarios, business rule edge cases

---

## Phase 3: Core Business Logic (Week 3)

### Issue #7: Time Calculation Engine
**Goal**: Implement accurate time and billing calculations

**Tasks**:
- Calculate billable hours: (End - Start - Break + Travel%)
- Handle overnight shifts (00:00 = next day)
- Create TimeDelta utilities for consistent handling
- Apply project-specific travel time rules

**Acceptance Criteria**:
- [ ] Calculates hours correctly for all time scenarios
- [ ] Handles overnight work properly
- [ ] Applies correct travel time percentages
- [ ] Matches Jupyter notebook calculations exactly

**Test Strategy**: Time calculation matrix, overnight edge cases

---

### Issue #8: Trip Duration Calculator
**Goal**: Implement sophisticated consecutive day grouping algorithm

**Tasks**:
- Detect consecutive on-site days per freelancer/project/location
- Calculate trip start dates and durations
- Handle gaps in consecutive days (new trips)
- Support same-day returns and multi-location trips

**Acceptance Criteria**:
- [ ] Groups consecutive days correctly
- [ ] Calculates trip durations accurately
- [ ] Handles edge cases (weekends, gaps, same-day)
- [ ] Matches Jupyter notebook trip logic exactly

**Test Strategy**: Complex trip scenarios, edge case matrix

---

### Issue #9: Billing Calculator
**Goal**: Calculate accurate billing amounts and profit margins

**Tasks**:
- Apply rates per freelancer-project combination
- Calculate hours billed, travel surcharge billed
- Calculate costs and agency profit margins
- Handle different billing rules per project

**Acceptance Criteria**:
- [ ] Applies correct rates for each freelancer-project pair
- [ ] Calculates travel surcharges correctly
- [ ] Computes agency profit margins accurately
- [ ] Handles missing rate information gracefully

**Test Strategy**: Rate application matrix, profit calculation verification

---

## Phase 4: Data Aggregation (Week 4)

### Issue #10: Timesheet Aggregator
**Goal**: Combine multiple freelancer timesheets into unified dataset

**Tasks**:
- Aggregate data from multiple timesheet sources
- Merge with project terms and trip calculations
- Implement filtering by date range, project, freelancer
- Handle large datasets efficiently

**Acceptance Criteria**:
- [ ] Combines all timesheet data correctly
- [ ] Merges terms and trip data accurately
- [ ] Supports flexible filtering
- [ ] Processes 30+ timesheets efficiently

**Test Strategy**: Large dataset tests, filtering validation

---

### Issue #11: Trip Aggregator
**Goal**: Extract and organize trip reimbursement data

**Tasks**:
- Extract trips with non-zero reimbursements
- Group trips by month for reporting
- Apply reimbursement rates based on duration/location
- Create trip summary statistics

**Acceptance Criteria**:
- [ ] Extracts only trips with reimbursements
- [ ] Groups trips correctly by month
- [ ] Applies correct reimbursement amounts
- [ ] Generates accurate trip summaries

**Test Strategy**: Trip filtering, reimbursement calculation tests

---

### Issue #12: Weekly Hours Calculator
**Goal**: Generate weekly capacity and utilization reports

**Tasks**:
- Calculate weekly hours per freelancer
- Generate week-by-week matrix (52 weeks)
- Handle year boundaries and week numbering
- Support filtering by project and date range

**Acceptance Criteria**:
- [ ] Calculates weekly totals correctly
- [ ] Handles year boundaries properly
- [ ] Generates proper matrix format
- [ ] Supports flexible date filtering

**Test Strategy**: Year boundary tests, week calculation verification

---

## Phase 5: Report Generation (Week 5)

### Issue #13: Master Timesheet Generator
**Goal**: Create formatted master timesheet matching expected output

**Tasks**:
- Generate complete timesheet with all required columns
- Apply proper data types and formatting
- Ensure column order matches expected output
- Handle thousands of rows efficiently

**Acceptance Criteria**:
- [ ] Generates all 24 required columns correctly
- [ ] Applies proper formatting to dates, times, numbers
- [ ] Maintains column order from original system
- [ ] Handles large datasets (9000+ rows)

**Test Strategy**: Output format validation, large dataset performance

---

### Issue #14: Pivot Table Builder
**Goal**: Create pivot table data for summary reporting

**Tasks**:
- Prepare pivot table data structure
- Implement filtering by project and time period
- Calculate summary statistics and totals
- Generate calculated fields (Total billed, Agency Profit)

**Acceptance Criteria**:
- [ ] Creates pivot data structure correctly
- [ ] Applies filters accurately
- [ ] Calculates summary statistics properly
- [ ] Generates calculated fields correctly

**Test Strategy**: Pivot calculation verification, filter testing

---

### Issue #15: Google Sheets Writer
**Goal**: Generate properly formatted Google Sheets output

**Tasks**:
- Create new spreadsheet with 4 sheets
- Apply cell formatting (currency, dates, colors)
- Set column widths and frozen rows/columns
- Generate pivot tables in Google Sheets API

**Acceptance Criteria**:
- [ ] Creates spreadsheet with correct sheet structure
- [ ] Applies formatting to match original output
- [ ] Sets proper column widths and freezing
- [ ] Generates working pivot tables

**Test Strategy**: Output formatting verification, Google Sheets API tests

---

## Phase 6: CLI Application (Week 6)

### Issue #16: CLI Interface
**Goal**: Create user-friendly command-line interface

**Tasks**:
- Implement Click-based CLI framework
- Create generate-report command with options
- Add list-timesheets and validate-data commands
- Provide progress indicators and error messages

**Acceptance Criteria**:
- [ ] CLI provides intuitive commands and help
- [ ] Generate-report command works end-to-end
- [ ] Progress indicators show processing status
- [ ] Error messages are clear and actionable

**Test Strategy**: CLI command testing, user experience validation

---

### Issue #17: Report Automation
**Goal**: Enable automated report generation and scheduling

**Tasks**:
- Add batch processing capabilities
- Implement configurable date ranges
- Create progress tracking and notifications
- Support dry-run mode for validation

**Acceptance Criteria**:
- [ ] Supports batch processing of multiple periods
- [ ] Provides configurable automation options
- [ ] Shows detailed progress and status
- [ ] Includes dry-run validation mode

**Test Strategy**: Automation workflow tests, batch processing validation

---

### Issue #18: Error Handling & Logging
**Goal**: Implement robust error handling and monitoring

**Tasks**:
- Add structured logging throughout application
- Implement comprehensive error handling
- Create error recovery mechanisms
- Add monitoring and alerting capabilities

**Acceptance Criteria**:
- [ ] Logs provide detailed debugging information
- [ ] Errors are handled gracefully with recovery
- [ ] Critical failures are reported clearly
- [ ] Performance metrics are tracked

**Test Strategy**: Error scenario testing, logging verification

---

## Phase 7: Testing & Documentation (Week 7)

### Issue #19: Integration Testing Suite
**Goal**: Ensure end-to-end system reliability

**Tasks**:
- Create comprehensive integration test scenarios
- Test with production-like data volumes
- Implement performance testing framework
- Test Google API rate limiting scenarios

**Acceptance Criteria**:
- [ ] Integration tests cover all major workflows
- [ ] Performance tests verify scalability
- [ ] Rate limiting is handled properly
- [ ] System works with real production data

**Test Strategy**: End-to-end scenarios, performance benchmarks

---

### Issue #20: Documentation & Deployment
**Goal**: Complete system documentation and deployment preparation

**Tasks**:
- Write comprehensive README with setup instructions
- Create user guide with examples and troubleshooting
- Document API and configuration options
- Prepare deployment scripts and Docker configuration

**Acceptance Criteria**:
- [ ] Documentation enables new user onboarding
- [ ] All configuration options are documented
- [ ] Deployment process is automated
- [ ] Troubleshooting guide covers common issues

**Test Strategy**: Documentation completeness, deployment verification

---

## Success Metrics

- **Test Coverage**: 90%+ across all modules
- **Accuracy**: 100% match with Jupyter notebook calculations
- **Performance**: Process 30 timesheets in < 10 seconds
- **Reliability**: Zero data loss or calculation errors
- **Automation**: Fully automated monthly report generation
- **Maintainability**: Clear code structure with comprehensive documentation

## Risk Mitigation

- **Google API Changes**: Mock layer isolates business logic from API specifics
- **Calculation Errors**: Extensive test suite with known good data
- **Performance Issues**: Early performance testing with realistic data volumes
- **Data Loss**: Validation and backup mechanisms throughout pipeline
- **Deployment Issues**: Containerized deployment with clear documentation

## Next Steps

1. **Repository Setup**: Initialize GitHub repository with issues
2. **Development Environment**: Set up local development environment
3. **Issue Assignment**: Begin with Issue #1 (Project Setup)
4. **Regular Reviews**: Weekly progress reviews and adjustments
5. **Continuous Integration**: Ensure all code changes maintain test coverage

This plan provides a clear roadmap for transforming the billing system while maintaining reliability and accuracy through comprehensive testing.
