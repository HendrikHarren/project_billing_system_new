# Migration Guide: Domain-Wide Delegation to Shared Drive

This guide explains how to migrate from the legacy domain-wide delegation authentication to the new direct service account access using Google Shared Drive.

## Table of Contents

1. [Overview](#overview)
2. [Why Migrate?](#why-migrate)
3. [Prerequisites](#prerequisites)
4. [Migration Steps](#migration-steps)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedure](#rollback-procedure)

---

## Overview

**What's changing:**
- **Old Method**: Service account impersonates a user via domain-wide delegation
- **New Method**: Service account accesses files directly via Shared Drive or file sharing

**Configuration changes:**
- Removed: `GOOGLE_SUBJECT_EMAIL` environment variable
- No longer needed: Google Workspace Admin Console configuration
- Required: Service account must be granted direct access to files/folders

**Timeline:**
- This migration was implemented in Issue #52 (October 2025)
- Old method still works in versions prior to this change
- New method is required from this version forward

---

## Why Migrate?

### Security Benefits

1. **Eliminates broad access**: Service account can no longer impersonate ANY user in your organization
2. **Principle of least privilege**: Access limited to explicitly shared resources only
3. **Reduces attack surface**: No domain-wide delegation means no potential for privilege escalation
4. **Google-recommended**: Aligns with Google's 2025 security best practices

### Operational Benefits

1. **Simpler setup**: No Google Workspace Admin configuration required
2. **Easier permission management**: Clear visibility of which service account has access
3. **Better collaboration**: Shared Drive provides team-wide access
4. **Audit trail**: Clearer access logs in Google Admin Console

### References

- [Google: Domain-wide delegation best practices (2025)](https://support.google.com/a/answer/14437356)
- [Google: Best practices for service accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)

---

## Prerequisites

Before starting the migration:

### 1. Identify Current Setup

Check your current configuration:

```bash
# View your current .env file
cat .env | grep GOOGLE_SUBJECT_EMAIL
```

If you see `GOOGLE_SUBJECT_EMAIL=...`, you're using domain-wide delegation and need to migrate.

### 2. Gather Information

You'll need:
- ✅ Service account email (from `.env`: `GOOGLE_CLIENT_EMAIL`)
- ✅ List of all Google Drive folders and files the system accesses:
  - Timesheet folder ID (`TIMESHEET_FOLDER_ID`)
  - Project terms file ID (`PROJECT_TERMS_FILE_ID`)
  - Output folder ID (`MONTHLY_INVOICING_FOLDER_ID`)
- ✅ Google Workspace admin access (for creating Shared Drive) OR ability to share files

### 3. Choose Access Method

**Option A: Shared Drive** (Recommended for Teams)
- **Pros**: Centralized permissions, easy team collaboration, better management
- **Cons**: Requires Google Workspace Business/Enterprise
- **Best for**: Multiple users, team environments, production deployments

**Option B: Direct File Sharing** (For Individual Users)
- **Pros**: Works with any Google account, simple setup
- **Cons**: Need to share each folder/file individually
- **Best for**: Single users, personal accounts, development/testing

---

## Migration Steps

### Step 1: Backup Current Configuration

```bash
# Backup your current .env file
cp .env .env.backup.$(date +%Y%m%d)

# Verify backup was created
ls -l .env.backup.*
```

### Step 2: Update Code to Latest Version

```bash
# Pull latest changes
git pull origin main

# Or checkout the specific branch with the migration
git checkout issue-52-migrate-from-domain-wide-delegation-to-direct-service-account-access-with-shared-drive

# Install/update dependencies
pip install -r requirements.txt
```

### Step 3A: Set Up Shared Drive Access (Recommended)

#### 3A.1: Create or Use Existing Shared Drive

1. Go to [Google Drive](https://drive.google.com/)
2. Click **Shared drives** in the left sidebar
3. Click **+ New** to create a new Shared Drive
4. Name it (e.g., "Billing System Files")
5. Click **Create**

#### 3A.2: Add Service Account to Shared Drive

1. Open the Shared Drive you just created
2. Click the **Settings** icon (gear) → **Manage members**
3. Click **Add members**
4. Enter your service account email (from `.env`: `GOOGLE_CLIENT_EMAIL`)
   - Example: `billing-system@my-project.iam.gserviceaccount.com`
5. Set role to **Content Manager** or **Manager**
6. Uncheck "Notify people" (service accounts don't receive emails)
7. Click **Send**

#### 3A.3: Move Files to Shared Drive

1. **Move timesheet folder:**
   - Locate your timesheet folder in My Drive
   - Right-click → **Move to** → Select your Shared Drive
   - Click **Move**

2. **Move project terms file:**
   - Locate your project terms spreadsheet in My Drive
   - Right-click → **Move to** → Select your Shared Drive
   - Click **Move**

3. **Move or create output folder:**
   - Locate your output folder in My Drive
   - Right-click → **Move to** → Select your Shared Drive
   - Or create a new folder directly in the Shared Drive

#### 3A.4: Update Folder/File IDs (if they changed)

**Important**: File/folder IDs remain the same when moving to Shared Drive, so you typically don't need to update them. However, verify with:

```bash
# List files in your Shared Drive to verify IDs
# Use the Google Drive web interface and check the URLs
```

If IDs changed, update your `.env` file accordingly.

### Step 3B: Set Up Direct File Sharing (Alternative)

If you can't use Shared Drive, share files individually:

#### 3B.1: Share Timesheet Folder

1. Go to [Google Drive](https://drive.google.com/)
2. Locate your timesheet folder
3. Right-click → **Share**
4. Enter your service account email (`GOOGLE_CLIENT_EMAIL` from `.env`)
5. Set permission to **Viewer** or **Editor**
6. Uncheck "Notify people"
7. Click **Share**

#### 3B.2: Share Project Terms File

1. Locate your project terms spreadsheet
2. Right-click → **Share**
3. Enter your service account email
4. Set permission to **Viewer**
5. Uncheck "Notify people"
6. Click **Share**

#### 3B.3: Share Output Folder

1. Locate your output folder
2. Right-click → **Share**
3. Enter your service account email
4. Set permission to **Editor** (required to create files)
5. Uncheck "Notify people"
6. Click **Share**

### Step 4: Update Configuration File

Edit your `.env` file and remove the `GOOGLE_SUBJECT_EMAIL` line:

```bash
# Open .env in your editor
nano .env

# Remove this line (entire line, not just the value):
# GOOGLE_SUBJECT_EMAIL=your-email@domain.com

# Save and exit (Ctrl+X, Y, Enter for nano)
```

**Before:**
```env
GOOGLE_CLIENT_EMAIL=billing-system@my-project.iam.gserviceaccount.com
GOOGLE_SUBJECT_EMAIL=admin@company.com    # ← Remove this line
```

**After:**
```env
GOOGLE_CLIENT_EMAIL=billing-system@my-project.iam.gserviceaccount.com
# GOOGLE_SUBJECT_EMAIL line removed
```

### Step 5: Remove Domain-Wide Delegation (Optional Cleanup)

If you're no longer using domain-wide delegation anywhere else, clean up:

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Security** → **API Controls** → **Domain-wide Delegation**
3. Find your service account's Client ID
4. Click **Remove** (only if not used elsewhere!)

**Warning**: Only do this if no other systems are using domain-wide delegation with this service account.

---

## Verification

### Test 1: Configuration Validation

```bash
# Validate new configuration
python scripts/validate_config.py
```

**Expected output:**
```
✓ Configuration loaded successfully
✓ Google Sheets API connection successful
✓ Google Drive API connection successful
✓ Timesheet folder accessible
✓ Project terms file accessible
✓ Output folder accessible
```

### Test 2: Connection Test

```bash
# Test Google API connection
python test_connection.py
```

**Expected output:**
```
Testing Google Sheets API...
✓ Successfully authenticated
✓ Connection successful

Testing Google Drive API...
✓ Successfully authenticated
✓ Connection successful

✓ All tests passed!
```

### Test 3: List Timesheets

```bash
# List available timesheets
python -m src.cli list-timesheets
```

**Expected output:**
```
Available Timesheets:
┌────────────────────────────────┬──────────────────────────────┬─────────────────────┐
│ Freelancer Name                │ File ID                      │ Last Modified       │
├────────────────────────────────┼──────────────────────────────┼─────────────────────┤
│ John Doe                       │ 1abc...                      │ 2025-10-05 14:30    │
│ Jane Smith                     │ 2def...                      │ 2025-10-05 15:45    │
...
```

### Test 4: Generate Test Report

```bash
# Generate a report for last month (replace with actual month)
python -m src.cli generate-report --month 2025-09
```

**Expected output:**
```
[1/5] Reading timesheet files...
[2/5] Aggregating data...
[3/5] Calculating billing amounts...
[4/5] Generating master timesheet...
[5/5] Writing to Google Sheets...

✓ Report generated successfully!
```

---

## Troubleshooting

### Issue: "Access denied" or "File not found" errors

**Cause**: Service account doesn't have access to files/folders

**Solutions:**

1. **Verify service account was added to Shared Drive:**
   ```bash
   # Check that you used the correct service account email
   cat .env | grep GOOGLE_CLIENT_EMAIL
   ```

2. **Verify service account role:**
   - Open Shared Drive settings
   - Check that service account has Content Manager or Manager role
   - Not just Viewer (needs to create files in output folder)

3. **Verify files are in Shared Drive (not My Drive):**
   - Files must be in Shared Drive, not just shared from My Drive
   - Move files to Shared Drive using steps in 3A.3

### Issue: "GOOGLE_SUBJECT_EMAIL is required" error

**Cause**: Running old version of the code

**Solution:**
```bash
# Pull latest changes
git pull origin main

# Verify you're on the correct version
git log --oneline -1
# Should show commit related to Issue #52
```

### Issue: Tests pass but report generation fails

**Cause**: Output folder doesn't have correct permissions

**Solution:**
1. Verify output folder (`MONTHLY_INVOICING_FOLDER_ID`) is in Shared Drive
2. Verify service account has **Editor** or **Manager** role (not just Viewer)
3. Test folder access:
   ```bash
   python -c "from src.services import GoogleDriveService; from src.config import get_config; config = get_config(); service = GoogleDriveService(config.get_google_service_account_info()); print(service.get_file_metadata(config.monthly_invoicing_folder_id))"
   ```

### Issue: "Invalid credentials" or authentication errors

**Cause**: Configuration issue with service account

**Solution:**
1. Verify `.env` file has all required variables (except GOOGLE_SUBJECT_EMAIL)
2. Check private key format (must have `\n` for newlines)
3. Test with validation script:
   ```bash
   python scripts/validate_config.py
   ```

### Issue: Migration works but old deployments break

**Cause**: Old code version still running elsewhere

**Solution:**
1. Update all deployments to the new version
2. Or temporarily keep `GOOGLE_SUBJECT_EMAIL` in `.env` (will be ignored by new code but old code will still work)
3. Plan coordinated deployment across all environments

---

## Rollback Procedure

If you need to revert to the old domain-wide delegation method:

### Step 1: Restore Backup

```bash
# Restore your backed-up .env file
cp .env.backup.YYYYMMDD .env

# Verify GOOGLE_SUBJECT_EMAIL is present
cat .env | grep GOOGLE_SUBJECT_EMAIL
```

### Step 2: Revert Code

```bash
# Checkout previous version (before Issue #52)
git checkout <previous-commit-hash>

# Or revert to main if you were on a branch
git checkout main
git pull origin main

# Reinstall dependencies
pip install -r requirements.txt
```

### Step 3: Verify

```bash
# Test connection with old method
python test_connection.py
```

### Step 4: Re-enable Domain-Wide Delegation (if removed)

1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Security** → **API Controls** → **Domain-wide Delegation**
3. Click **Add new**
4. Enter Client ID from service account JSON
5. Add scopes:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive`
6. Click **Authorize**

---

## Post-Migration Checklist

- [ ] Backup of old `.env` file created
- [ ] Code updated to latest version
- [ ] Service account added to Shared Drive (or files shared directly)
- [ ] All files moved to Shared Drive (or shared individually)
- [ ] `GOOGLE_SUBJECT_EMAIL` removed from `.env`
- [ ] Configuration validation passed (`python scripts/validate_config.py`)
- [ ] Connection test passed (`python test_connection.py`)
- [ ] List timesheets test passed (`python -m src.cli list-timesheets`)
- [ ] Report generation test passed (`python -m src.cli generate-report --month YYYY-MM`)
- [ ] All environments updated (dev, staging, production)
- [ ] Team notified of migration
- [ ] Documentation reviewed
- [ ] (Optional) Domain-wide delegation removed from Admin Console

---

## Additional Resources

- [Configuration Reference](CONFIGURATION.md) - Complete environment variable documentation
- [User Guide](USER_GUIDE.md) - Step-by-step setup instructions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Google Shared Drive Documentation](https://support.google.com/a/users/answer/9310156)
- [Google Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)

---

## Support

If you encounter issues not covered in this guide:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [Issue #52](https://github.com/HendrikHarren/project_billing_system_new/issues/52) on GitHub
3. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - Your configuration (without sensitive data)
   - Whether using Shared Drive or direct sharing

---

**Migration completed on:** <!-- Add date when completed -->
**Tested by:** <!-- Add your name -->
**Issues encountered:** <!-- Add any issues for future reference -->
