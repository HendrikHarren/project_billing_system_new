# Billing System User Guide

Welcome to the Billing System! This guide will walk you through setting up and using the system to generate comprehensive billing reports from freelancer timesheets.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Google API Setup](#google-api-setup)
3. [First Report Generation](#first-report-generation)
4. [CLI Commands Reference](#cli-commands-reference)
5. [Common Workflows](#common-workflows)
6. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- **Python 3.9 or higher** installed
- **Git** for cloning the repository
- **Google Workspace account** with admin access (for creating service accounts)
- **Access to freelancer timesheets** in Google Sheets

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/HendrikHarren/project_billing_system_new.git
   cd project_billing_system_new
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python -m src.cli --version
   ```

You should see the application version number displayed.

---

## Google API Setup

The billing system uses Google Service Accounts to access Google Sheets and Drive. Follow these steps to set up API access.

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name (e.g., "Billing System")
4. Click **Create**

### Step 2: Enable Required APIs

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for and enable:
   - **Google Sheets API**
   - **Google Drive API**

### Step 3: Create a Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Enter service account details:
   - **Name**: `billing-system-service-account`
   - **Description**: `Service account for automated billing report generation`
4. Click **Create and Continue**
5. Skip granting roles (click **Continue**)
6. Click **Done**

### Step 4: Create Service Account Key

1. Click on the newly created service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create**
6. Save the downloaded JSON file securely (e.g., `service-account-key.json`)

⚠️ **Security Warning**: This file contains sensitive credentials. Never commit it to version control!

### Step 5: Grant Service Account Access to Files

The service account needs direct access to your Google Sheets and Drive folders. You have two options:

#### Option A: Shared Drive (Recommended for Teams)

1. **Create or use existing Shared Drive**
   - Go to [Google Drive](https://drive.google.com/)
   - Click **Shared drives** → **New** (if creating new)
   - Give it a name (e.g., "Billing System Data")

2. **Add service account to Shared Drive**
   - Open the Shared Drive
   - Click **Manage members**
   - Add the service account email (from JSON key file: `client_email`)
   - Grant **Content Manager** or **Manager** role
   - Click **Send**

3. **Move your files to the Shared Drive**
   - Move timesheet folder, project terms file, and output folder to this Shared Drive
   - All team members and the service account will have access

#### Option B: Direct File Sharing (For Individual Users)

1. **Share timesheet folder**
   - Open the timesheet folder in Google Drive
   - Click **Share**
   - Add the service account email (found in JSON key file as `client_email`)
   - Grant **Viewer** access
   - Click **Send**

2. **Share project terms file**
   - Open the project terms spreadsheet
   - Click **Share**
   - Add the service account email
   - Grant **Viewer** access
   - Click **Send**

3. **Share output folder**
   - Open the monthly invoicing folder
   - Click **Share**
   - Add the service account email
   - Grant **Editor** access (required to create new files)
   - Click **Send**

### Step 6: Configure Environment Variables

1. **Copy the example environment file**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your credentials**

   Open `.env` in a text editor and fill in the values from your `service-account-key.json`:

   ```env
   # Google Cloud Project Configuration
   GOOGLE_PROJECT_ID=your-project-id
   GOOGLE_PRIVATE_KEY_ID=your-private-key-id
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n"
   GOOGLE_CLIENT_EMAIL=billing-system-service-account@your-project.iam.gserviceaccount.com
   GOOGLE_CLIENT_ID=123456789012345678901
   GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

   # Google Drive and Sheets IDs
   TIMESHEET_FOLDER_ID=your-timesheet-folder-id
   PROJECT_TERMS_FILE_ID=your-project-terms-file-id
   MONTHLY_INVOICING_FOLDER_ID=your-output-folder-id
   ```

   **Note**: The service account must have direct access to these files/folders (via Shared Drive or direct sharing).

3. **Find Google Drive Folder and File IDs**

   The IDs are in the URLs:
   - **Folder**: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - **File**: `https://docs.google.com/spreadsheets/d/FILE_ID_HERE/edit`

4. **Test the connection**
   ```bash
   python test_connection.py
   ```

   You should see:
   ```
   ✓ Configuration loaded successfully
   ✓ Google Sheets API connection successful
   ✓ Google Drive API connection successful
   ✓ Timesheet folder accessible
   ✓ Project terms file accessible
   ```

---

## First Report Generation

Now that everything is set up, let's generate your first billing report!

### Step 1: List Available Timesheets

Check which timesheets are available:

```bash
python -m src.cli list-timesheets
```

**Example output:**
```
Available Timesheets
┌──────────────────┬─────────────────────────────┬─────────────────────┐
│ Freelancer       │ File ID                     │ Last Modified       │
├──────────────────┼─────────────────────────────┼─────────────────────┤
│ John Doe         │ 1abc...xyz                  │ 2024-10-01 14:30    │
│ Jane Smith       │ 2def...uvw                  │ 2024-10-02 09:15    │
│ Mike Johnson     │ 3ghi...rst                  │ 2024-10-01 16:45    │
└──────────────────┴─────────────────────────────┴─────────────────────┘
```

### Step 2: Validate Data Quality (Optional)

Before generating a report, validate your data:

```bash
python -m src.cli validate-data --month 2024-10
```

**Example output:**
```
Validating timesheets for 2024-10...
✓ Loaded 3 timesheets
✓ Validated 156 entries

Validation Summary:
  Errors: 0
  Warnings: 2
  Info: 5

Warnings:
  - [2024-10-15] John Doe: Break time (120 min) seems high for 8-hour shift
  - [2024-10-20] Jane Smith: Work duration (12.5 hours) is unusually long
```

### Step 3: Generate Monthly Report

Generate a billing report for a specific month:

```bash
python -m src.cli generate-report --month 2024-10
```

**What happens:**
1. ✓ Reads all freelancer timesheets from Google Drive
2. ✓ Loads project terms and billing rates
3. ✓ Validates data quality
4. ✓ Calculates billable hours and amounts
5. ✓ Identifies trips for reimbursement
6. ✓ Generates master timesheet with 4 sheets:
   - **Timesheet_master**: Detailed billing entries
   - **Trips_master**: Travel reimbursements
   - **Pivot_master**: Financial summary (native pivot table)
   - **Weekly_reporting**: Weekly hours matrix (native pivot table)
7. ✓ Uploads to Google Sheets in the output folder

**Example output:**
```
[1/5] Reading timesheets...
  ✓ Loaded 32 timesheets (1,247 entries)

[2/5] Aggregating data...
  ✓ Filtered to 156 entries for 2024-10
  ✓ Calculated billing for 156 entries

[3/5] Generating master timesheet...
  ✓ Generated Timesheet_master (156 rows)
  ✓ Generated Trips_master (12 trips)

[4/5] Creating Google Sheets...
  ✓ Created spreadsheet: "Billing Report - 2024-10"
  ✓ Applied formatting and pivot tables

[5/5] Moving to output folder...
  ✓ Moved to Monthly Invoicing folder

Report generated successfully! ✓
  File ID: 1xyz...abc
  URL: https://docs.google.com/spreadsheets/d/1xyz...abc/edit
  Duration: 8.3 seconds
```

### Step 4: Review the Report

1. Open the URL provided in the output
2. Review the 4 sheets:
   - **Timesheet_master**: Verify individual entries
   - **Trips_master**: Check travel reimbursements
   - **Pivot_master**: Review financial summaries by project/freelancer
   - **Weekly_reporting**: Analyze weekly capacity utilization

---

## CLI Commands Reference

### `generate-report`

Generate a comprehensive billing report.

**Basic usage:**
```bash
python -m src.cli generate-report --month YYYY-MM
```

**Options:**
- `--month YYYY-MM`: Month to generate report for (e.g., `2024-10`)
- `--project CODE`: Filter by specific project code
- `--freelancer NAME`: Filter by freelancer name
- `--start-date YYYY-MM-DD`: Custom start date
- `--end-date YYYY-MM-DD`: Custom end date

**Examples:**

```bash
# Generate report for October 2024
python -m src.cli generate-report --month 2024-10

# Generate report for specific project
python -m src.cli generate-report --month 2024-10 --project PROJ001

# Generate report for specific freelancer
python -m src.cli generate-report --month 2024-10 --freelancer "John Doe"

# Generate report for custom date range
python -m src.cli generate-report --start-date 2024-10-01 --end-date 2024-10-15

# Combine filters
python -m src.cli generate-report --month 2024-10 --project PROJ001 --freelancer "Jane Smith"
```

### `list-timesheets`

List all available timesheets in the configured folder.

**Usage:**
```bash
python -m src.cli list-timesheets [OPTIONS]
```

**Options:**
- `--folder-id ID`: Override default timesheet folder ID

**Example:**
```bash
# List all timesheets
python -m src.cli list-timesheets

# List timesheets from different folder
python -m src.cli list-timesheets --folder-id 1abc...xyz
```

### `validate-data`

Validate timesheet data quality and business rules.

**Usage:**
```bash
python -m src.cli validate-data [OPTIONS]
```

**Options:**
- `--month YYYY-MM`: Validate data for specific month
- `--file-id ID`: Validate specific timesheet file
- `--severity LEVEL`: Minimum severity to display (`error`, `warning`, `info`)

**Examples:**

```bash
# Validate all timesheets
python -m src.cli validate-data

# Validate specific month
python -m src.cli validate-data --month 2024-10

# Validate specific file
python -m src.cli validate-data --file-id 1abc...xyz

# Show only errors
python -m src.cli validate-data --severity error

# Show errors and warnings
python -m src.cli validate-data --severity warning
```

---

## Common Workflows

### Monthly Billing Cycle

**Typical monthly workflow:**

1. **First week of the month** - Validate previous month's data
   ```bash
   python -m src.cli validate-data --month 2024-10
   ```

2. **Fix any validation errors** in the Google Sheets timesheets

3. **Generate the report**
   ```bash
   python -m src.cli generate-report --month 2024-10
   ```

4. **Review the report** in Google Sheets

5. **Export for invoicing** (use Google Sheets export features)

### Project-Specific Reporting

Generate reports for specific projects:

```bash
# Monthly report for specific project
python -m src.cli generate-report --month 2024-10 --project PROJ001

# Quarterly report for a project
python -m src.cli generate-report --start-date 2024-07-01 --end-date 2024-09-30 --project PROJ001
```

### Freelancer-Specific Reporting

Generate reports for individual freelancers:

```bash
# Monthly report for one freelancer
python -m src.cli generate-report --month 2024-10 --freelancer "John Doe"

# Annual report for a freelancer
python -m src.cli generate-report --start-date 2024-01-01 --end-date 2024-12-31 --freelancer "Jane Smith"
```

### Data Quality Checks

Regular validation workflow:

```bash
# Weekly validation
python -m src.cli validate-data --severity warning

# Pre-report validation
python -m src.cli validate-data --month 2024-10 --severity error

# Freelancer-specific validation
python -m src.cli validate-data --file-id 1abc...xyz
```

---

## Best Practices

### Data Entry

1. **Consistent formatting**: Ensure freelancers follow the same format in timesheets
2. **Regular updates**: Encourage daily or weekly timesheet updates
3. **Validate frequently**: Run validation weekly to catch errors early
4. **Project codes**: Use consistent project codes across all timesheets

### Report Generation

1. **Test before production**: Run validation before generating final reports
2. **Use filters wisely**: Filter by project or freelancer for faster processing
3. **Regular backups**: Download reports for archival purposes
4. **Review pivot tables**: Use the native pivot tables for quick insights

### Performance Optimization

1. **Enable caching**: Keep `ENABLE_SHEETS_CACHE=True` in `.env` (default)
2. **Date filtering**: Use date filters to reduce data volume
3. **Batch processing**: Generate reports during off-peak hours
4. **Monitor API quotas**: Watch for Google API quota warnings

### Security

1. **Protect credentials**: Never commit `.env` file to version control
2. **Rotate keys**: Periodically rotate service account keys
3. **Limit permissions**: Grant minimum necessary Google API permissions
4. **Audit access**: Review who has access to timesheets and reports

### Troubleshooting

For common issues and solutions, see the [Troubleshooting Guide](TROUBLESHOOTING.md).

For configuration details, see the [Configuration Reference](CONFIGURATION.md).

For deployment instructions, see the [Deployment Guide](DEPLOYMENT.md).

---

## Next Steps

Now that you're familiar with the basics:

1. **Customize your workflow**: Adapt the commands to your specific needs
2. **Automate reports**: Set up scheduled report generation (see [Deployment Guide](DEPLOYMENT.md))
3. **Explore advanced features**: Read the [Architecture documentation](ARCHITECTURE.md)
4. **Contribute**: Help improve the system by reporting issues or contributing code

For questions or support, please [create an issue](https://github.com/HendrikHarren/project_billing_system_new/issues) on GitHub.

---

**Happy billing! 📊**
