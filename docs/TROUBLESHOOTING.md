# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Billing System.

## Table of Contents

1. [Authentication & API Errors](#authentication--api-errors)
2. [Configuration Issues](#configuration-issues)
3. [Data Validation Errors](#data-validation-errors)
4. [Performance Issues](#performance-issues)
5. [CLI Errors](#cli-errors)
6. [Google Sheets/Drive Issues](#google-sheetsdrive-issues)
7. [Debug Mode](#debug-mode)
8. [Getting Help](#getting-help)

---

## Authentication & API Errors

### Error: "Could not load credentials"

**Symptoms:**
```
Error: Could not load credentials from environment variables
```

**Causes:**
- Missing or incorrect `.env` file
- Environment variables not set correctly
- Invalid JSON format in `GOOGLE_PRIVATE_KEY`

**Solutions:**

1. **Verify `.env` file exists**
   ```bash
   ls -la .env
   ```

2. **Check required variables are set**
   ```bash
   # On Unix/macOS
   grep GOOGLE .env

   # Or load and check
   source .env
   echo $GOOGLE_PROJECT_ID
   ```

3. **Validate private key format**
   - Ensure the private key includes literal `\n` (not actual newlines)
   - Format should be:
     ```env
     GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQI...\n-----END PRIVATE KEY-----\n"
     ```

4. **Re-download service account key**
   - Go to Google Cloud Console
   - Create a new key for the service account
   - Update `.env` with new credentials

### Error: "Insufficient authentication scopes"

**Symptoms:**
```
google.auth.exceptions.RefreshError: Insufficient authentication scopes
```

**Causes:**
- Service account doesn't have required API access
- Service account not granted direct access to files/folders

**Solutions:**

1. **Verify APIs are enabled**
   - Google Sheets API
   - Google Drive API

2. **Grant service account access to files**

   **Option A: Shared Drive (Recommended)**
   - Add service account to Shared Drive as Content Manager or Manager
   - Move all files/folders to the Shared Drive

   **Option B: Direct Sharing**
   - Share Google Sheets/folders directly with service account email
   - Grant Editor or Viewer permissions as needed

### Error: "Permission denied"

**Symptoms:**
```
googleapiclient.errors.HttpError: <HttpError 403 when requesting ... returned "Permission denied">
```

**Causes:**
- Service account doesn't have access to files/folders
- Incorrect folder/file IDs
- Files not shared with service account

**Solutions:**

1. **Verify file/folder IDs**
   ```bash
   # Check IDs in .env
   grep FOLDER_ID .env
   grep FILE_ID .env
   ```

2. **Share files with service account**
   - Open Google Sheet or folder
   - Click Share
   - Add service account email (`xxx@xxx.iam.gserviceaccount.com`)
   - Grant appropriate permissions

3. **Test file access**
   ```bash
   python test_connection.py
   ```

---

## Configuration Issues

### Error: "TIMESHEET_FOLDER_ID not found"

**Symptoms:**
```
ValidationError: TIMESHEET_FOLDER_ID is required
```

**Causes:**
- `.env` file missing required variables
- Variable names misspelled

**Solutions:**

1. **Copy example file**
   ```bash
   cp .env.example .env
   ```

2. **Check variable names** (case-sensitive!)
   Required variables:
   - `GOOGLE_PROJECT_ID`
   - `GOOGLE_PRIVATE_KEY`
   - `GOOGLE_CLIENT_EMAIL`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_PRIVATE_KEY_ID`
   - `GOOGLE_CLIENT_X509_CERT_URL`
   - `TIMESHEET_FOLDER_ID`
   - `PROJECT_TERMS_FILE_ID`
   - `MONTHLY_INVOICING_FOLDER_ID`

3. **Validate configuration**
   ```bash
   python -c "from src.config.settings import Settings; Settings()"
   ```

### Error: "Invalid GOOGLE_PRIVATE_KEY format"

**Symptoms:**
```
ValueError: Invalid private key format
```

**Causes:**
- Newlines not properly escaped
- Missing begin/end markers
- Extra quotes or spaces

**Solutions:**

1. **Check key format**
   The key should be a single line with `\n` for newlines:
   ```env
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...\n-----END PRIVATE KEY-----\n"
   ```

2. **Don't use actual newlines**
   ❌ Wrong:
   ```env
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
   MIIEvQIBADANBg...
   -----END PRIVATE KEY-----"
   ```

   ✅ Correct:
   ```env
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...\n-----END PRIVATE KEY-----\n"
   ```

---

## Data Validation Errors

### Error: "Invalid date format"

**Symptoms:**
```
ValidationError: Date must be in YYYY-MM-DD format: '10/15/2024'
```

**Causes:**
- Timesheet uses wrong date format
- Mixed date formats in same sheet

**Solutions:**

1. **Standardize date format in timesheets**
   - Use ISO format: `YYYY-MM-DD` (e.g., `2024-10-15`)
   - Or use European: `DD.MM.YYYY` (e.g., `15.10.2024`)

2. **Check for Excel serial dates**
   - If dates appear as numbers (e.g., `45234`), format cells as dates in Google Sheets

3. **Update timesheet column formatting**
   - Select date column → Format → Number → Date

### Error: "Break time exceeds work time"

**Symptoms:**
```
ValidationError: Break time (120 min) cannot exceed work time (60 min)
```

**Causes:**
- Data entry error in timesheet
- Swapped start/end times
- Invalid overnight shift

**Solutions:**

1. **Check timesheet entry**
   - Verify start time < end time
   - For overnight shifts, end time should be `00:00` or later

2. **Validate break time**
   - Break should be less than total work duration
   - Typical breaks: 30-60 minutes

3. **Run validation to identify all issues**
   ```bash
   python -m src.cli validate-data --month 2024-10 --severity error
   ```

### Error: "Unknown project code"

**Symptoms:**
```
ValidationError: Project code 'PROJ999' not found in project terms
```

**Causes:**
- Typo in project code
- Project not added to project terms sheet
- Case sensitivity mismatch

**Solutions:**

1. **Check project terms sheet**
   - Verify project code exists
   - Check spelling and case

2. **Update project code in timesheet**
   - Use exact project code from project terms
   - Project codes are case-sensitive

3. **Add new project to project terms**
   - Add row in project terms sheet
   - Include rate, cost, and other required fields

---

## Performance Issues

### Slow report generation (> 30 seconds)

**Symptoms:**
- Report generation takes very long
- System appears to hang

**Causes:**
- Too many timesheet entries (thousands)
- Cache disabled
- Large date range
- Slow network connection

**Solutions:**

1. **Enable caching**
   ```env
   ENABLE_SHEETS_CACHE=True
   CACHE_AUTO_SAVE=True
   ```

2. **Use date filters**
   ```bash
   # Filter by month (much faster than full year)
   python -m src.cli generate-report --month 2024-10

   # Instead of:
   python -m src.cli generate-report --start-date 2024-01-01 --end-date 2024-12-31
   ```

3. **Optimize timesheet folder**
   - Remove or archive old timesheets
   - Keep only active freelancers in the folder

4. **Check network speed**
   - Google API calls require stable internet
   - Use wired connection if possible

### High memory usage

**Symptoms:**
- System runs out of memory
- Python process killed

**Causes:**
- Very large datasets (10,000+ entries)
- Memory leak in data processing

**Solutions:**

1. **Use filters to reduce data volume**
   ```bash
   python -m src.cli generate-report --month 2024-10 --project PROJ001
   ```

2. **Process data in batches**
   - Split large date ranges into monthly reports
   - Combine afterwards if needed

3. **Increase available memory**
   - Close other applications
   - Consider using a machine with more RAM

### Rate limiting errors

**Symptoms:**
```
google.api_core.exceptions.ResourceExhausted: Quota exceeded for quota metric 'Read requests'
```

**Causes:**
- Too many API calls in short period
- Multiple instances running simultaneously
- Large number of timesheets

**Solutions:**

1. **Wait and retry**
   - Google API quotas reset after 100 seconds
   - Wait 2 minutes and try again

2. **Enable caching** (prevents repeated API calls)
   ```env
   ENABLE_SHEETS_CACHE=True
   ```

3. **Reduce concurrent requests**
   - Don't run multiple report generations simultaneously
   - Space out report generation jobs

4. **Request quota increase**
   - Go to Google Cloud Console → APIs & Services → Quotas
   - Request higher quota for Google Sheets API

---

## CLI Errors

### Error: "No module named 'src'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Causes:**
- Virtual environment not activated
- Not running from project root directory
- Dependencies not installed

**Solutions:**

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # Unix/macOS
   venv\Scripts\activate     # Windows
   ```

2. **Verify current directory**
   ```bash
   pwd  # Should show project_billing_system_new
   ls   # Should see src/, tests/, docs/, etc.
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Error: "Invalid month format"

**Symptoms:**
```
Error: Invalid month format. Use YYYY-MM (e.g., 2024-10)
```

**Causes:**
- Wrong date format in `--month` parameter

**Solutions:**

1. **Use correct format**
   ```bash
   # ✅ Correct
   python -m src.cli generate-report --month 2024-10

   # ❌ Wrong
   python -m src.cli generate-report --month 10-2024
   python -m src.cli generate-report --month October
   python -m src.cli generate-report --month 10/2024
   ```

### Error: "Click command not found"

**Symptoms:**
```
Error: No such command 'generate-report'
```

**Causes:**
- Typo in command name
- Using old/incorrect command

**Solutions:**

1. **Check available commands**
   ```bash
   python -m src.cli --help
   ```

2. **Use correct command names**
   - `generate-report` (with hyphen, not underscore)
   - `list-timesheets`
   - `validate-data`

---

## Google Sheets/Drive Issues

### Error: "Spreadsheet not found"

**Symptoms:**
```
HttpError 404: File not found
```

**Causes:**
- Incorrect file/folder ID
- File deleted or moved
- Service account doesn't have access

**Solutions:**

1. **Verify file ID**
   - Open file in browser
   - Copy ID from URL: `https://docs.google.com/spreadsheets/d/FILE_ID_HERE/edit`

2. **Check file still exists**
   - Search for file in Google Drive
   - Verify it hasn't been deleted

3. **Re-share with service account**
   - Open file → Share
   - Add service account email
   - Grant appropriate permissions

### Error: "Unable to create spreadsheet"

**Symptoms:**
```
HttpError 403: Insufficient permissions to create file
```

**Causes:**
- Service account doesn't have write access to output folder
- Output folder doesn't exist
- Wrong folder ID
- Output folder not in Shared Drive or not shared directly

**Solutions:**

1. **Grant service account access to output folder**

   **Option A: Shared Drive (Recommended)**
   - Move `MONTHLY_INVOICING_FOLDER_ID` folder to Shared Drive
   - Ensure service account has Content Manager or Manager role

   **Option B: Direct Sharing**
   - Open `MONTHLY_INVOICING_FOLDER_ID` folder
   - Share with service account email
   - Grant **Editor** permissions

2. **Verify folder ID**
   ```bash
   grep MONTHLY_INVOICING_FOLDER_ID .env
   ```

3. **Test folder access**
   ```bash
   python test_connection.py
   ```

### Pivot tables not working

**Symptoms:**
- Pivot tables appear but don't show data
- Pivot tables show #REF errors

**Causes:**
- Source data range incorrect
- Filters applied incorrectly
- Data sheet name changed

**Solutions:**

1. **Refresh pivot table**
   - Right-click pivot table → Refresh

2. **Check source data range**
   - Verify pivot table references correct sheet
   - Ensure data range includes all rows

3. **Clear and recreate filters**
   - Remove all filters
   - Add filters one by one

---

## Debug Mode

Enable detailed logging to diagnose issues:

### Enable Debug Logging

```bash
# Set environment variables
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run command
python -m src.cli generate-report --month 2024-10
```

### Debug Output

With debug mode enabled, you'll see:
- Detailed API call logs
- Data processing steps
- Cache hit/miss information
- Timing information for each step

### Log Files

Logs are written to console by default. To save to file:

```bash
python -m src.cli generate-report --month 2024-10 2>&1 | tee debug.log
```

### Common Debug Checks

1. **Verify configuration**
   ```python
   from src.config.settings import Settings
   settings = Settings()
   print(settings.dict())
   ```

2. **Test Google API connection**
   ```python
   from src.services.google_auth import create_google_service
   service = create_google_service('sheets')
   print("Connection successful!")
   ```

3. **Check cache status**
   ```python
   from src.services.sheets_cache_service import SheetsCacheService
   cache = SheetsCacheService()
   print(f"Cache entries: {cache.get_cache_size()}")
   ```

---

### Shared Drive Access Issues

**Symptoms:**
- Files accessible in browser but not via API
- Inconsistent permission errors

**Causes:**
- Service account not added to Shared Drive
- Insufficient role in Shared Drive
- Files in "My Drive" instead of Shared Drive

**Solutions:**

1. **Verify Shared Drive membership**
   - Open Shared Drive → Manage members
   - Ensure service account is listed
   - Check role is Content Manager or Manager

2. **Move files to Shared Drive**
   - Files must be IN the Shared Drive, not just shared
   - Right-click file → Move to → Select Shared Drive

3. **Check folder structure**
   - All configured folders must be in same Shared Drive
   - Or all must have direct sharing with service account

---

## Getting Help

### Still having issues?

1. **Search existing issues**
   - Check [GitHub Issues](https://github.com/HendrikHarren/project_billing_system_new/issues)
   - Search for similar problems

2. **Create a new issue**
   - Go to [New Issue](https://github.com/HendrikHarren/project_billing_system_new/issues/new)
   - Include:
     - Error message (full traceback)
     - Steps to reproduce
     - Configuration (hide sensitive data!)
     - Python version (`python --version`)
     - Debug log output
     - Whether using Shared Drive or direct sharing

3. **Provide diagnostic information**
   ```bash
   # System info
   python --version
   pip list | grep google

   # Test connection
   python test_connection.py

   # Validation output
   python -m src.cli validate-data --severity error
   ```

### Useful Resources

- [User Guide](USER_GUIDE.md) - Step-by-step setup and usage
- [Configuration Reference](CONFIGURATION.md) - Environment variables
- [Architecture Documentation](ARCHITECTURE.md) - System design
- [GitHub Issues](https://github.com/HendrikHarren/project_billing_system_new/issues) - Bug reports and feature requests

---

**Remember**: Most issues are related to configuration or Google API permissions. Ensure your service account has proper access via Shared Drive or direct file sharing!
