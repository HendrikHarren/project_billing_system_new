"""
Google API authentication module for the billing system.
"""

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build


def load_credentials() -> Dict[str, Any]:
    """Load Google service account credentials from environment variables."""
    load_dotenv()

    required_vars = [
        "GOOGLE_PROJECT_ID",
        "GOOGLE_PRIVATE_KEY_ID",
        "GOOGLE_PRIVATE_KEY",
        "GOOGLE_CLIENT_EMAIL",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_AUTH_URI",
        "GOOGLE_TOKEN_URI",
        "GOOGLE_AUTH_PROVIDER_X509_CERT_URL",
        "GOOGLE_CLIENT_X509_CERT_URL",
    ]

    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")

    return {
        "type": "service_account",
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY"),
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
    }


def get_credentials(
    scopes: Optional[list[str]] = None,
) -> service_account.Credentials:
    """Get authenticated credentials for Google APIs."""
    if scopes is None:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

    credentials_info = load_credentials()
    subject_email = os.getenv("GOOGLE_SUBJECT_EMAIL")

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=scopes, subject=subject_email
    )

    return credentials


def get_sheets_service():
    """Get authenticated Google Sheets service."""
    credentials = get_credentials()
    return build("sheets", "v4", credentials=credentials)


def get_drive_service():
    """Get authenticated Google Drive service."""
    credentials = get_credentials()
    return build("drive", "v3", credentials=credentials)
