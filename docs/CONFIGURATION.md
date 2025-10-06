# Configuration Reference

Complete reference for all environment variables and configuration options in the Billing System.

## Table of Contents

1. [Configuration File](#configuration-file)
2. [Google API Configuration](#google-api-configuration)
3. [Google Drive/Sheets Configuration](#google-drivesheets-configuration)
4. [Application Configuration](#application-configuration)
5. [Processing Configuration](#processing-configuration)
6. [Cache Configuration](#cache-configuration)
7. [Example Configurations](#example-configurations)
8. [Security Best Practices](#security-best-practices)
9. [Validation](#validation)

---

## Configuration File

The Billing System uses environment variables for configuration, loaded from a `.env` file.

### Setup

1. **Copy the example file**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Set required variables**
   - See [Required Variables](#required-variables) section below

### File Format

```env
# Comments start with #
VARIABLE_NAME=value

# Multi-line values use quotes and \n
MULTI_LINE="Line 1\nLine 2\nLine 3"

# Boolean values
ENABLE_FEATURE=true  # or false

# Numeric values
MAX_RETRIES=3
RETRY_DELAY=1.5
```

---

## Google API Configuration

These variables configure authentication with Google Cloud APIs.

### Required Variables

#### `GOOGLE_PROJECT_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Your Google Cloud project ID
- **Where to find**: [Google Cloud Console](https://console.cloud.google.com/) → Project dropdown
- **Example**: `my-billing-project-123456`

#### `GOOGLE_PRIVATE_KEY_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Service account private key ID
- **Where to find**: Service account JSON key file (`private_key_id` field)
- **Example**: `abc123def456...`

#### `GOOGLE_PRIVATE_KEY`
- **Type**: String (multi-line)
- **Required**: Yes
- **Description**: Service account private key (PEM format)
- **Format**: Must include `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`
- **Important**: Use `\n` for line breaks, not actual newlines
- **Where to find**: Service account JSON key file (`private_key` field)
- **Example**:
  ```env
  GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w...\n-----END PRIVATE KEY-----\n"
  ```

#### `GOOGLE_CLIENT_EMAIL`
- **Type**: String (email)
- **Required**: Yes
- **Description**: Service account email address
- **Where to find**: Service account JSON key file (`client_email` field)
- **Example**: `billing-system@my-project.iam.gserviceaccount.com`

#### `GOOGLE_CLIENT_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Service account client ID
- **Where to find**: Service account JSON key file (`client_id` field)
- **Example**: `123456789012345678901`

#### `GOOGLE_CLIENT_X509_CERT_URL`
- **Type**: String (URL)
- **Required**: Yes
- **Description**: Service account X.509 certificate URL
- **Where to find**: Service account JSON key file (`client_x509_cert_url` field)
- **Example**: `https://www.googleapis.com/robot/v1/metadata/x509/billing-system%40my-project.iam.gserviceaccount.com`

#### `GOOGLE_SUBJECT_EMAIL`
- **Type**: String (email)
- **Required**: Yes (for domain-wide delegation)
- **Description**: Email address to impersonate for domain-wide delegation
- **When needed**: Required if using domain-wide delegation
- **Example**: `admin@yourdomain.com`

### Optional Variables

#### `GOOGLE_AUTH_URI`
- **Type**: String (URL)
- **Required**: No
- **Default**: `https://accounts.google.com/o/oauth2/auth`
- **Description**: Google OAuth2 authorization endpoint

#### `GOOGLE_TOKEN_URI`
- **Type**: String (URL)
- **Required**: No
- **Default**: `https://oauth2.googleapis.com/token`
- **Description**: Google OAuth2 token endpoint

#### `GOOGLE_AUTH_PROVIDER_X509_CERT_URL`
- **Type**: String (URL)
- **Required**: No
- **Default**: `https://www.googleapis.com/oauth2/v1/certs`
- **Description**: Google OAuth2 certificate provider URL

---

## Google Drive/Sheets Configuration

These variables specify which Google Drive folders and Sheets to use.

### Required Variables

#### `TIMESHEET_FOLDER_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Google Drive folder containing individual freelancer timesheets
- **Where to find**: Folder URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
- **Permissions**: Service account needs **Viewer** or **Editor** access
- **Example**: `1GGQdjwFNf0u2-4FqwtkL7sKKx6iwqfVm`

#### `PROJECT_TERMS_FILE_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Google Sheets file with project terms (rates, costs, travel rules)
- **Where to find**: Spreadsheet URL: `https://docs.google.com/spreadsheets/d/FILE_ID_HERE/edit`
- **Permissions**: Service account needs **Viewer** access
- **Example**: `14JHBLil55qWyezueHdrsSN5psUqdzjWd7HJaPkmIzY0`

#### `MONTHLY_INVOICING_FOLDER_ID`
- **Type**: String
- **Required**: Yes
- **Description**: Google Drive folder for generated billing reports
- **Where to find**: Folder URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
- **Permissions**: Service account needs **Editor** access (to create files)
- **Example**: `1yerh1sIIM8KebKuy-QSDhnXfr4q88uPE`

---

## Application Configuration

General application settings.

### Optional Variables

#### `ENVIRONMENT`
- **Type**: String (enum)
- **Required**: No
- **Default**: `development`
- **Valid values**: `development`, `testing`, `production`
- **Description**: Application environment
- **Use cases**:
  - `development`: Local development with verbose logging
  - `testing`: CI/CD pipeline and automated tests
  - `production`: Production deployment with optimized settings

#### `DEBUG`
- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Valid values**: `true`, `false`
- **Description**: Enable debug mode with detailed logging
- **Impact**: Enables verbose output, stack traces, and debug logs

#### `LOG_LEVEL`
- **Type**: String (enum)
- **Required**: No
- **Default**: `INFO`
- **Valid values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Minimum logging level
- **Recommendations**:
  - `DEBUG`: Troubleshooting and development
  - `INFO`: Normal operation (default)
  - `WARNING`: Production with less verbosity
  - `ERROR`: Minimal logging (errors only)

---

## Processing Configuration

Settings that control data processing behavior.

### Optional Variables

#### `BATCH_SIZE`
- **Type**: Integer
- **Required**: No
- **Default**: `10`
- **Range**: `1` - `100`
- **Description**: Number of timesheets to process in parallel batches
- **Impact**:
  - Higher values: Faster processing, more memory usage
  - Lower values: Slower processing, less memory usage
- **Recommendations**:
  - Small datasets (< 10 files): `5-10`
  - Medium datasets (10-30 files): `10-20`
  - Large datasets (> 30 files): `20-50`

#### `MAX_RETRIES`
- **Type**: Integer
- **Required**: No
- **Default**: `3`
- **Range**: `0` - `10`
- **Description**: Maximum number of retry attempts for failed API calls
- **Impact**: Higher values increase reliability but may increase processing time
- **Recommendations**:
  - Stable network: `3`
  - Unreliable network: `5-7`
  - Fast failure: `1-2`

#### `RETRY_DELAY`
- **Type**: Float (seconds)
- **Required**: No
- **Default**: `1.0`
- **Range**: `0.1` - `10.0`
- **Description**: Initial delay before retry (exponential backoff)
- **Impact**: Delay doubles with each retry (1s → 2s → 4s → 8s)
- **Recommendations**:
  - Fast retry: `0.5`
  - Normal: `1.0`
  - Conservative: `2.0`

---

## Cache Configuration

Settings for the dual-layer caching system (see [CACHING.md](CACHING.md) for details).

### Optional Variables

#### `ENABLE_SHEETS_CACHE`
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Valid values**: `true`, `false`
- **Description**: Enable/disable Google Sheets caching
- **Impact**:
  - `true`: 60-90% reduction in API calls, faster processing
  - `false`: Fresh data on every run, slower processing
- **Recommendations**:
  - **Enable** (default) for production and normal usage
  - **Disable** only for testing or debugging cache issues

#### `CACHE_FILE_PATH`
- **Type**: String (file path)
- **Required**: No
- **Default**: `.cache/sheets_cache.json`
- **Description**: Location of persistent cache file
- **Recommendations**:
  - Keep default for single-user setup
  - Use absolute path for multi-user deployments
  - Ensure directory is writable
- **Example**: `/var/cache/billing-system/sheets_cache.json`

#### `CACHE_MAX_SIZE`
- **Type**: Integer
- **Required**: No
- **Default**: `100`
- **Range**: `10` - `1000`
- **Description**: Maximum number of cache entries (LRU eviction)
- **Impact**: Higher values use more memory but cache more files
- **Recommendations**:
  - Small projects (< 20 files): `50`
  - Medium projects (20-50 files): `100` (default)
  - Large projects (> 50 files): `200-500`

#### `CACHE_AUTO_SAVE`
- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Valid values**: `true`, `false`
- **Description**: Automatically save cache to disk on updates
- **Impact**:
  - `true`: Cache persists across restarts (recommended)
  - `false`: Cache cleared on application exit
- **Recommendations**: Keep enabled unless testing

---

## Example Configurations

### Development Environment

Recommended for local development and testing:

```env
# Google API Configuration (from service account JSON)
GOOGLE_PROJECT_ID=my-billing-dev-project
GOOGLE_PRIVATE_KEY_ID=abc123...
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=billing-dev@my-project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=123456789012345678901
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
GOOGLE_SUBJECT_EMAIL=developer@company.com

# Google Drive/Sheets IDs
TIMESHEET_FOLDER_ID=1GGQdjwFNf0u2-4FqwtkL7sKKx6iwqfVm
PROJECT_TERMS_FILE_ID=14JHBLil55qWyezueHdrsSN5psUqdzjWd7HJaPkmIzY0
MONTHLY_INVOICING_FOLDER_ID=1yerh1sIIM8KebKuy-QSDhnXfr4q88uPE

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Processing Configuration
BATCH_SIZE=5
MAX_RETRIES=3
RETRY_DELAY=1.0

# Cache Configuration
ENABLE_SHEETS_CACHE=true
CACHE_FILE_PATH=.cache/sheets_cache.json
CACHE_MAX_SIZE=50
CACHE_AUTO_SAVE=true
```

### Production Environment

Recommended for production deployment:

```env
# Google API Configuration (from service account JSON)
GOOGLE_PROJECT_ID=my-billing-prod-project
GOOGLE_PRIVATE_KEY_ID=xyz789...
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=billing-prod@my-project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=987654321098765432109
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
GOOGLE_SUBJECT_EMAIL=admin@company.com

# Google Drive/Sheets IDs
TIMESHEET_FOLDER_ID=1abc...production-folder
PROJECT_TERMS_FILE_ID=2def...production-file
MONTHLY_INVOICING_FOLDER_ID=3ghi...production-output

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Processing Configuration
BATCH_SIZE=20
MAX_RETRIES=5
RETRY_DELAY=2.0

# Cache Configuration
ENABLE_SHEETS_CACHE=true
CACHE_FILE_PATH=/var/cache/billing-system/sheets_cache.json
CACHE_MAX_SIZE=200
CACHE_AUTO_SAVE=true
```

### Testing Environment

Recommended for CI/CD and automated testing:

```env
# Google API Configuration (test service account)
GOOGLE_PROJECT_ID=my-billing-test-project
GOOGLE_PRIVATE_KEY_ID=test123...
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=billing-test@my-project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=111222333444555666777
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
GOOGLE_SUBJECT_EMAIL=test@company.com

# Google Drive/Sheets IDs (test data)
TIMESHEET_FOLDER_ID=1test...folder
PROJECT_TERMS_FILE_ID=2test...file
MONTHLY_INVOICING_FOLDER_ID=3test...output

# Application Configuration
ENVIRONMENT=testing
DEBUG=false
LOG_LEVEL=WARNING

# Processing Configuration
BATCH_SIZE=5
MAX_RETRIES=1
RETRY_DELAY=0.5

# Cache Configuration
ENABLE_SHEETS_CACHE=false  # Disable for testing fresh data
CACHE_FILE_PATH=/tmp/test_cache.json
CACHE_MAX_SIZE=10
CACHE_AUTO_SAVE=false
```

---

## Security Best Practices

### Protecting Credentials

1. **Never commit `.env` file to version control**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment-specific files**
   ```bash
   .env.development
   .env.testing
   .env.production
   ```

3. **Restrict file permissions**
   ```bash
   chmod 600 .env  # Read/write for owner only
   ```

4. **Use secrets management in production**
   - Docker secrets
   - Kubernetes secrets
   - AWS Secrets Manager
   - Google Secret Manager
   - HashiCorp Vault

### Rotating Credentials

Periodically rotate service account keys:

1. **Create new service account key**
   - Go to Google Cloud Console
   - Create new key for service account

2. **Update `.env` with new credentials**

3. **Test connection**
   ```bash
   python test_connection.py
   ```

4. **Delete old key**
   - Only after verifying new key works

### Minimal Permissions

Grant service account only necessary permissions:

- **Sheets API**: Required for reading/writing spreadsheets
- **Drive API**: Required for file operations
- **Folder access**: Share only specific folders, not entire Drive

---

## Validation

### Validate Configuration

Check if configuration is valid:

```bash
python -c "from src.config.settings import get_config; config = get_config(); print('✓ Configuration valid')"
```

### Test Google API Connection

Verify Google API credentials work:

```bash
python test_connection.py
```

**Expected output:**
```
✓ Configuration loaded successfully
✓ Google Sheets API connection successful
✓ Google Drive API connection successful
✓ Timesheet folder accessible
✓ Project terms file accessible
```

### Validation Script

Create a custom validation script:

```python
#!/usr/bin/env python
"""Validate configuration and test connections."""

from src.config.settings import get_config
from src.services.google_auth import create_google_service

def validate_config():
    """Validate all configuration settings."""
    try:
        config = get_config()
        print("✓ Configuration loaded")

        # Test Google Sheets API
        sheets_service = create_google_service("sheets")
        print("✓ Google Sheets API connection successful")

        # Test Google Drive API
        drive_service = create_google_service("drive")
        print("✓ Google Drive API connection successful")

        # Test folder access
        drive_service.files().get(fileId=config.timesheet_folder_id).execute()
        print("✓ Timesheet folder accessible")

        # Test file access
        sheets_service.spreadsheets().get(
            spreadsheetId=config.project_terms_file_id
        ).execute()
        print("✓ Project terms file accessible")

        print("\n✓ All validation checks passed!")
        return True

    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_config()
```

### Common Validation Errors

See [Troubleshooting Guide](TROUBLESHOOTING.md#configuration-issues) for solutions to common configuration errors.

---

## Related Documentation

- [User Guide](USER_GUIDE.md) - Step-by-step setup and usage
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Caching Guide](CACHING.md) - Cache system details
- [Deployment Guide](DEPLOYMENT.md) - Production deployment

---

**Remember**: Keep your `.env` file secure and never commit it to version control!
