# System Architecture

## Overview

The billing system transforms freelancer timesheet data from Google Sheets into comprehensive billing reports using a modular Python architecture with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Google Drive  │    │  Google Sheets  │    │ Project Terms   │
│  (Timesheets)   │    │   (Individual   │    │   (Rates &      │
│                 │    │   Freelancer    │    │   Rules)        │
│                 │    │   Data)         │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Collection Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Drive     │  │ Timesheet   │  │   Project Terms         │ │
│  │  Service    │  │  Reader     │  │     Reader              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Data Validation Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Timesheet  │  │ Business    │  │     Data Quality        │ │
│  │ Validation  │  │    Rule     │  │     Reporting           │ │
│  │            │  │ Validation  │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Business Logic Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │    Time     │  │    Trip     │  │       Billing           │ │
│  │ Calculator  │  │  Duration   │  │     Calculator          │ │
│  │            │  │ Calculator  │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                Data Aggregation Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Timesheet   │  │    Trip     │  │      Weekly             │ │
│  │ Aggregator  │  │ Aggregator  │  │     Calculator          │ │
│  │            │  │             │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                Output Generation Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Master    │  │   Pivot     │  │     Google Sheets       │ │
│  │ Timesheet   │  │   Table     │  │       Writer            │ │
│  │ Generator   │  │  Builder    │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Interface                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Generate   │  │  Validate   │  │       List              │ │
│  │   Report    │  │    Data     │  │   Timesheets            │ │
│  │            │  │             │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### Configuration Layer (`src/config/`)

**Purpose**: Centralized configuration management with validation

**Components**:
- `settings.py`: Pydantic-based configuration with environment variable loading
- Validates Google API credentials and required settings
- Supports multiple environments (development, testing, production)

**Key Features**:
- Type-safe configuration with validation
- Environment variable override support
- Google service account credential management

### Services Layer (`src/services/`)

**Purpose**: External service integration and API management

**Components**:
- `google_auth.py`: Google API authentication and service creation
- `sheets_service.py`: Google Sheets API wrapper with retry logic
- `drive_service.py`: Google Drive API wrapper for file operations

**Key Features**:
- Connection pooling and retry mechanisms
- Rate limiting handling
- Mock-friendly interfaces for testing

### Data Models (`src/models/`)

**Purpose**: Type-safe data structures for business entities

**Components**:
- `timesheet.py`: Timesheet entry data structure
- `project.py`: Project and project terms data structures
- `trip.py`: Trip and reimbursement data structures
- `freelancer.py`: Freelancer information data structure

**Key Features**:
- Pydantic models with validation
- Serialization/deserialization support
- Business rule validation

### Readers Layer (`src/readers/`)

**Purpose**: Data extraction from Google Sheets with error handling

**Components**:
- `timesheet_reader.py`: ✅ Extract individual freelancer timesheets
  - Supports multiple date formats (ISO, European, US)
  - Handles multiple time formats (HH:MM, H:MM)
  - Normalizes location data (On-site/Off-site to onsite/remote)
  - Extracts freelancer name from sheet title
  - Gracefully handles missing and malformed data
  - 99% test coverage with 40 unit tests
- `project_terms_reader.py`: ✅ Load project rates and billing terms
  - In-memory caching with configurable TTL (default: 1 hour)
  - Loads main project terms (rates, costs, percentages)
  - Loads trip reimbursement terms
  - Case-sensitive freelancer-project lookups
  - Decimal precision for financial calculations
  - 96% test coverage with 30 unit tests
- `base_reader.py`: Common reading functionality and error handling (planned)

**Key Features**:
- ✅ Robust data parsing with type conversion
- ✅ Missing data handling with logging
- ✅ Overnight shift detection
- ✅ Whitespace and edge case handling
- ✅ In-memory caching with TTL and manual invalidation
- ✅ Lazy loading for optimal performance

### Validators Layer (`src/validators/`)

**Purpose**: Data quality and business rule compliance validation

**Components**:
- `validation_report.py`: ✅ Validation issue tracking and reporting
  - ValidationSeverity enum (INFO, WARNING, ERROR)
  - ValidationIssue dataclass for individual issues
  - ValidationReport for collecting and formatting issues
  - Context support for detailed error messages
  - 100% test coverage with 19 unit tests
- `field_validators.py`: ✅ Field-level validation
  - Date validation (format, range, future/old date warnings)
  - Time validation (24-hour format)
  - String validation (non-empty, whitespace)
  - Numeric validation (positive, non-negative, range)
  - Location validation (remote/onsite)
  - Project code validation
  - 100% test coverage with 32 unit tests
- `business_validators.py`: ✅ Business rule validation
  - Time range logic (normal vs overnight shifts)
  - Break time validation (< work time, reasonableness)
  - Profit margin validation (cost < rate)
  - Work duration warnings (unusually long/short)
  - Complete timesheet entry validation
  - Complete project terms validation
  - 100% test coverage with 24 unit tests
- `validator.py`: ✅ Main validation orchestrator
  - TimesheetValidator class for unified validation
  - Single entry and batch validation
  - Flexible validation modes (fields only, full validation)
  - Context-aware error messages with row numbers
  - Project terms validation
  - 100% test coverage with 12 unit tests

**Key Features**:
- ✅ Comprehensive field and business rule validation
- ✅ Clear, actionable error messages
- ✅ Severity-based issue categorization (error/warning/info)
- ✅ Flexible validation modes for different scenarios
- ✅ Context-aware validation with row numbers and metadata
- ✅ Graceful error handling with detailed reports
- ✅ 100% test coverage across all validator components (87 tests)

### Calculators Layer (`src/calculators/`)

**Purpose**: Core business logic for time and billing calculations

**Components**:
- `time_utils.py`: ✅ Low-level time calculation utilities
  - Convert dt.time to minutes since midnight
  - Calculate duration between times (with overnight support)
  - Convert timedelta to decimal hours with precision
  - Timezone-agnostic calculations
  - 100% test coverage with 23 unit tests
- `time_calculator.py`: ✅ Billable hours and amount calculation
  - Calculate work duration (end - start) with overnight support
  - Calculate billable hours: Work - Break + (Travel% × TravelTime)
  - Calculate billable amounts: Hours × Rate
  - Calculate travel surcharges for on-site work
  - Decimal precision for currency calculations
  - 100% test coverage with 14 unit tests
- `trip_calculator.py`: Consecutive day detection for trip duration (planned)
- `billing_calculator.py`: Rate application and profit margin calculation (planned)

**Key Features**:
- ✅ Accurate overnight shift handling (00:00 = next day)
- ✅ Travel time percentage calculations
- ✅ Project-specific billing rules
- ✅ Decimal precision for financial accuracy
- ✅ Matches Jupyter notebook calculations exactly
- ✅ 100% test coverage across all components (37 tests)

### Aggregators Layer (`src/aggregators/`)

**Purpose**: Data combination and summary generation

**Components**:
- `timesheet_aggregator.py`: Combine multiple freelancer timesheets
- `trip_aggregator.py`: Extract and organize trip reimbursements
- `weekly_calculator.py`: Generate weekly capacity reports

**Key Features**:
- Efficient large dataset processing
- Flexible filtering and grouping
- Memory-efficient aggregation

### Writers Layer (`src/writers/`)

**Purpose**: Output generation with proper formatting

**Components**:
- `master_timesheet_generator.py`: Generate formatted master timesheet
- `pivot_builder.py`: Create pivot table data structures
- `sheets_writer.py`: Write formatted output to Google Sheets

**Key Features**:
- Professional formatting and styling
- Pivot table generation
- Large dataset output handling

## Data Flow

### 1. Data Collection Phase

```
Google Sheets ──► Timesheet Reader ──► Raw Timesheet Data
   (30+ files)        (Parsing &           (Validated)
                      Validation)

Project Terms ──► Terms Reader ──► Billing Rules
   Sheet              (Caching)        (Cached)
```

### 2. Processing Phase

```
Raw Data ──► Time Calculator ──► Hours Calculated
             (Business Rules)      (With Travel)
                   │
                   ▼
            Trip Calculator ──► Trip Durations
            (Consecutive        (Grouped by
             Day Detection)      Location/Project)
                   │
                   ▼
            Billing Calculator ──► Financial Data
            (Rate Application)     (Billed Amounts,
                                   Profit Margins)
```

### 3. Aggregation Phase

```
Processed Data ──► Timesheet Aggregator ──► Master Dataset
(Multiple            (Combine + Filter)        (9000+ rows)
 Freelancers)               │
                           ▼
                    Trip Aggregator ──► Trip Summary
                    (Extract Trips)      (Reimbursements)
                           │
                           ▼
                    Weekly Calculator ──► Weekly Matrix
                    (Hours by Week)       (52 weeks × N freelancers)
```

### 4. Output Generation Phase

```
Master Dataset ──► Master Generator ──► Formatted Timesheet
                   (24 columns)           (All Details)
                          │
                          ▼
                   Pivot Builder ──► Summary Views
                   (Filters &         (Project/Period
                    Calculations)      Summaries)
                          │
                          ▼
                   Sheets Writer ──► Google Sheets
                   (4 Sheets +        (Published
                    Formatting)        Report)
```

## Key Algorithms

### Trip Duration Detection

**Problem**: Identify consecutive on-site days for travel reimbursement

**Algorithm**:
```python
# Group consecutive days using pandas groupby with cumsum
consecutive_groups = (
    ~(date_diff_is_consecutive & same_freelancer & same_location & same_project)
).cumsum()

trip_duration = max_date_in_group - min_date_in_group + 1_day
```

**Complexity**: O(n log n) due to sorting by date

### Billing Calculation

**Implementation**: `src/calculators/time_calculator.py`

**Formula**:
```python
# Calculate work duration (handles overnight shifts)
work_duration = end_time - start_time  # with overnight support

# Calculate billable hours
billable_hours = work_duration - break_time + (travel_time × travel_percentage / 100)

# Calculate billable amount
hours_billed = billable_hours × hourly_rate

# Calculate travel surcharge (only for on-site work)
travel_surcharge = (location == "onsite") ? billable_hours × hourly_rate × surcharge_percentage / 100 : 0

# Total billing
total_billed = hours_billed + travel_surcharge
agency_profit = total_billed - total_cost
```

**Example**:
```python
# 8-hour shift with 30-minute break and 60 minutes travel at 50% billable
entry = TimesheetEntry(start_time="09:00", end_time="17:00", break_minutes=30, travel_time_minutes=60)
terms = ProjectTerms(hourly_rate=85.00, travel_time_percentage=50.0, travel_surcharge_percentage=15.0)

# Calculation: 8 hours - 0.5 hours + (1 hour × 0.5) = 8.0 billable hours
billable_hours = 8.0
hours_billed = 8.0 × 85.00 = 680.00
travel_surcharge = 8.0 × 85.00 × 0.15 = 102.00
total_billed = 680.00 + 102.00 = 782.00
```

### Weekly Aggregation

**Approach**: Pivot table transformation
```python
weekly_matrix = timesheets.pivot_table(
    index='freelancer_name',
    columns='week_number',
    values='hours',
    aggfunc='sum',
    fill_value=0
)
```

## Error Handling Strategy

### Layered Error Handling

1. **Input Validation**: Pydantic models catch data format errors
2. **Business Rules**: Custom validators ensure logical consistency
3. **API Errors**: Retry logic with exponential backoff
4. **Processing Errors**: Graceful degradation with detailed logging

### Error Recovery

- **Missing Data**: Use defaults or skip with warnings
- **API Rate Limits**: Automatic retry with exponential backoff
- **Calculation Errors**: Isolate to individual freelancer/project
- **Output Errors**: Partial success with error reporting

## Performance Considerations

### Scalability

- **Memory**: Stream processing for large datasets
- **Network**: Batch API calls and connection pooling
- **CPU**: Vectorized operations using pandas
- **Storage**: Minimal intermediate file creation

### Optimization Techniques

- **Caching**: Project terms cached for session duration
- **Batching**: Process timesheets in configurable batch sizes
- **Parallel Processing**: Independent freelancer processing
- **Lazy Loading**: Data loaded only when needed

## Security

### Data Protection

- **Credentials**: Environment variables only, never in code
- **API Access**: Minimal required scopes
- **Data Handling**: No persistent storage of sensitive data
- **Logging**: Sanitized logs without credentials

### Access Control

- **Service Account**: Limited Google API permissions
- **File Access**: Read-only access to source data
- **Output**: Write access only to designated output folder

## Testing Architecture

### Test Pyramid

```
        ┌─────────────┐
        │ Integration │  (Real Google APIs, E2E workflows)
        │    Tests    │
        └─────────────┘
      ┌─────────────────┐
      │  Unit Tests     │    (Mocked dependencies, fast)
      │  (90% of tests) │
      └─────────────────┘
```

### Test Strategies

- **Unit Tests**: Mock external dependencies, focus on business logic
- **Integration Tests**: Real API calls with test data
- **Fixtures**: Shared test data for consistent scenarios
- **Property-Based Testing**: Generate edge cases automatically

## Deployment Architecture

### Environment Separation

- **Development**: Local with test Google account
- **Testing**: CI/CD with mock services
- **Production**: Scheduled execution with monitoring

### Monitoring

- **Logging**: Structured logs with correlation IDs
- **Metrics**: Processing time, success rates, error counts
- **Alerting**: Critical failures and data quality issues
- **Health Checks**: API connectivity and data availability

This architecture provides a robust, scalable, and maintainable foundation for the billing system while ensuring accuracy and reliability in financial calculations.
