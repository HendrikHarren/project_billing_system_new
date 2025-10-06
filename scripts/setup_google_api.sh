#!/bin/bash
#
# Interactive Google API setup helper
# Guides users through Google Cloud and service account setup
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Google API Setup Helper${NC}"
echo -e "${BLUE}  Billing System Configuration${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

echo "This script will guide you through setting up Google API access."
echo "You'll need:"
echo "  - Google Cloud Console access"
echo "  - Permission to create projects and service accounts"
echo "  - Access to Google Workspace Admin (for domain-wide delegation)"
echo ""
read -p "Press Enter to continue..."

# Step 1: Create Google Cloud Project
echo ""
echo -e "${GREEN}Step 1: Create Google Cloud Project${NC}"
echo "-----------------------------------"
echo "1. Go to: https://console.cloud.google.com/"
echo "2. Click 'Select a project' → 'New Project'"
echo "3. Enter project name (e.g., 'billing-system')"
echo "4. Click 'Create'"
echo "5. Note your Project ID"
echo ""
read -p "Enter your Google Cloud Project ID: " PROJECT_ID
echo "✓ Project ID: $PROJECT_ID"

# Step 2: Enable APIs
echo ""
echo -e "${GREEN}Step 2: Enable Required APIs${NC}"
echo "----------------------------"
echo "1. Go to: https://console.cloud.google.com/apis/library"
echo "2. Search for and enable:"
echo "   - Google Sheets API"
echo "   - Google Drive API"
echo ""
read -p "Press Enter when APIs are enabled..."
echo "✓ APIs enabled"

# Step 3: Create Service Account
echo ""
echo -e "${GREEN}Step 3: Create Service Account${NC}"
echo "-------------------------------"
echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts"
echo "2. Click 'Create Service Account'"
echo "3. Enter details:"
echo "   - Name: billing-system-service-account"
echo "   - Description: Service account for automated billing reports"
echo "4. Click 'Create and Continue'"
echo "5. Skip role assignment (click 'Continue')"
echo "6. Click 'Done'"
echo ""
read -p "Press Enter when service account is created..."
echo "✓ Service account created"

# Step 4: Create Service Account Key
echo ""
echo -e "${GREEN}Step 4: Create Service Account Key${NC}"
echo "------------------------------------"
echo "1. Click on the service account you just created"
echo "2. Go to 'Keys' tab"
echo "3. Click 'Add Key' → 'Create new key'"
echo "4. Select 'JSON' format"
echo "5. Click 'Create'"
echo "6. Save the downloaded JSON file"
echo ""
read -p "Enter path to downloaded JSON key file: " KEY_FILE

if [ ! -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}Warning: File not found. Please verify the path.${NC}"
    read -p "Enter path again: " KEY_FILE
fi

# Extract values from JSON
if [ -f "$KEY_FILE" ]; then
    echo "✓ Key file found"
    GOOGLE_CLIENT_EMAIL=$(python3 -c "import json; print(json.load(open('$KEY_FILE'))['client_email'])")
    echo "✓ Service account email: $GOOGLE_CLIENT_EMAIL"
else
    echo -e "${YELLOW}Warning: Could not read key file${NC}"
fi

# Step 5: Domain-Wide Delegation (Optional)
echo ""
echo -e "${GREEN}Step 5: Enable Domain-Wide Delegation (Optional)${NC}"
echo "------------------------------------------------"
echo "Only needed if you want to impersonate users in your Google Workspace."
echo ""
read -p "Do you need domain-wide delegation? (y/n): " NEED_DWD

if [[ "$NEED_DWD" =~ ^[Yy]$ ]]; then
    echo ""
    echo "1. In the service account details, enable 'Google Workspace Domain-wide Delegation'"
    echo "2. Go to: https://admin.google.com/"
    echo "3. Navigate to: Security → API Controls → Domain-wide Delegation"
    echo "4. Click 'Add new'"
    echo "5. Enter Client ID (from the JSON key file)"
    echo "6. Add OAuth scopes:"
    echo "   https://www.googleapis.com/auth/spreadsheets"
    echo "   https://www.googleapis.com/auth/drive"
    echo "7. Click 'Authorize'"
    echo ""
    read -p "Enter email to impersonate: " SUBJECT_EMAIL
    echo "✓ Subject email: $SUBJECT_EMAIL"
fi

# Step 6: Share Files
echo ""
echo -e "${GREEN}Step 6: Share Google Sheets and Folders${NC}"
echo "---------------------------------------"
echo "Share the following with your service account ($GOOGLE_CLIENT_EMAIL):"
echo "  1. Timesheet folder (grant Viewer or Editor access)"
echo "  2. Project terms spreadsheet (grant Viewer access)"
echo "  3. Output folder for reports (grant Editor access)"
echo ""
read -p "Press Enter when files are shared..."
echo "✓ Files shared"

# Step 7: Get File/Folder IDs
echo ""
echo -e "${GREEN}Step 7: Collect File and Folder IDs${NC}"
echo "------------------------------------"
echo "You'll need the IDs from the URLs:"
echo "  Folder: https://drive.google.com/drive/folders/FOLDER_ID_HERE"
echo "  File: https://docs.google.com/spreadsheets/d/FILE_ID_HERE/edit"
echo ""
read -p "Enter Timesheet Folder ID: " TIMESHEET_FOLDER_ID
read -p "Enter Project Terms File ID: " PROJECT_TERMS_FILE_ID
read -p "Enter Output Folder ID: " MONTHLY_INVOICING_FOLDER_ID

# Step 8: Generate .env file
echo ""
echo -e "${GREEN}Step 8: Generate .env File${NC}"
echo "--------------------------"

ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    read -p ".env file already exists. Overwrite? (y/n): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        ENV_FILE=".env.new"
        echo "Creating $ENV_FILE instead..."
    fi
fi

# Extract all values from JSON key file
if [ -f "$KEY_FILE" ]; then
    python3 << EOF
import json
import sys

with open('$KEY_FILE', 'r') as f:
    key_data = json.load(f)

with open('$ENV_FILE', 'w') as f:
    f.write("# Google API Configuration\n")
    f.write(f"GOOGLE_PROJECT_ID={key_data['project_id']}\n")
    f.write(f"GOOGLE_PRIVATE_KEY_ID={key_data['private_key_id']}\n")
    f.write(f"GOOGLE_PRIVATE_KEY=\"{key_data['private_key']}\"\n")
    f.write(f"GOOGLE_CLIENT_EMAIL={key_data['client_email']}\n")
    f.write(f"GOOGLE_CLIENT_ID={key_data['client_id']}\n")
    f.write(f"GOOGLE_CLIENT_X509_CERT_URL={key_data['client_x509_cert_url']}\n")
    f.write("\n# Domain-wide delegation (if enabled)\n")
    f.write("GOOGLE_SUBJECT_EMAIL=${SUBJECT_EMAIL:-your-email@domain.com}\n")
    f.write("\n# Google Drive/Sheets Configuration\n")
    f.write(f"TIMESHEET_FOLDER_ID=$TIMESHEET_FOLDER_ID\n")
    f.write(f"PROJECT_TERMS_FILE_ID=$PROJECT_TERMS_FILE_ID\n")
    f.write(f"MONTHLY_INVOICING_FOLDER_ID=$MONTHLY_INVOICING_FOLDER_ID\n")
    f.write("\n# Application Configuration\n")
    f.write("ENVIRONMENT=development\n")
    f.write("DEBUG=false\n")
    f.write("LOG_LEVEL=INFO\n")
    f.write("\n# Cache Configuration\n")
    f.write("ENABLE_SHEETS_CACHE=true\n")
    f.write("CACHE_FILE_PATH=.cache/sheets_cache.json\n")
    f.write("CACHE_MAX_SIZE=100\n")
    f.write("CACHE_AUTO_SAVE=true\n")

print(f"✓ Created {ENV_FILE}")
EOF
    echo "✓ Environment file created: $ENV_FILE"
fi

# Step 9: Test Connection
echo ""
echo -e "${GREEN}Step 9: Test Connection${NC}"
echo "-----------------------"
echo "Testing Google API connection..."
echo ""

if python3 test_connection.py 2>/dev/null; then
    echo ""
    echo -e "${GREEN}✓ Setup completed successfully!${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠ Connection test failed. Please review the configuration.${NC}"
    echo "Run 'python test_connection.py' for detailed error messages."
fi

# Final summary
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Setup Summary${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Service Account: $GOOGLE_CLIENT_EMAIL"
echo "Environment file: $ENV_FILE"
echo ""
echo "Next steps:"
echo "  1. Review $ENV_FILE and adjust settings as needed"
echo "  2. Run 'python test_connection.py' to verify setup"
echo "  3. Try generating a report:"
echo "     python -m src.cli generate-report --month $(date +%Y-%m)"
echo ""
echo "For more information, see docs/USER_GUIDE.md"
echo ""
