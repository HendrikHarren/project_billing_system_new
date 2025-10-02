"""
Configuration management for the billing system.
"""

from typing import List, Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSystemConfig(BaseSettings):
    """Configuration settings for the billing system."""

    # Google API Configuration
    google_project_id: str = Field(alias="GOOGLE_PROJECT_ID")
    google_private_key_id: str = Field(alias="GOOGLE_PRIVATE_KEY_ID")
    google_private_key: str = Field(alias="GOOGLE_PRIVATE_KEY")
    google_client_email: str = Field(alias="GOOGLE_CLIENT_EMAIL")
    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_auth_uri: str = Field(
        default="https://accounts.google.com/o/oauth2/auth", alias="GOOGLE_AUTH_URI"
    )
    google_token_uri: str = Field(
        default="https://oauth2.googleapis.com/token", alias="GOOGLE_TOKEN_URI"
    )
    google_auth_provider_x509_cert_url: str = Field(
        default="https://www.googleapis.com/oauth2/v1/certs",
        alias="GOOGLE_AUTH_PROVIDER_X509_CERT_URL",
    )
    google_client_x509_cert_url: str = Field(alias="GOOGLE_CLIENT_X509_CERT_URL")
    google_subject_email: str = Field(alias="GOOGLE_SUBJECT_EMAIL")

    # Google API Scopes
    google_scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )

    # Google Drive/Sheets Configuration
    timesheet_folder_id: str = Field(alias="TIMESHEET_FOLDER_ID")
    project_terms_file_id: str = Field(alias="PROJECT_TERMS_FILE_ID")
    monthly_invoicing_folder_id: str = Field(alias="MONTHLY_INVOICING_FOLDER_ID")

    # Application Configuration
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Processing Configuration
    batch_size: int = Field(default=10, alias="BATCH_SIZE")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay: float = Field(default=1.0, alias="RETRY_DELAY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
    )

    @field_validator("google_private_key")
    @classmethod
    def validate_private_key(cls, v):
        """Ensure private key has correct format."""
        if not v.startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError("Invalid private key format")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Ensure environment is valid."""
        valid_envs = ["development", "testing", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    def get_google_service_account_info(self) -> dict:
        """Get Google service account info as dictionary."""
        return {
            "type": "service_account",
            "project_id": self.google_project_id,
            "private_key_id": self.google_private_key_id,
            "private_key": self.google_private_key,
            "client_email": self.google_client_email,
            "client_id": self.google_client_id,
            "auth_uri": self.google_auth_uri,
            "token_uri": self.google_token_uri,
            "auth_provider_x509_cert_url": self.google_auth_provider_x509_cert_url,
            "client_x509_cert_url": self.google_client_x509_cert_url,
        }


def load_config(env_file: Optional[str] = None) -> BillingSystemConfig:
    """Load configuration from environment variables and .env file."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    return BillingSystemConfig()


# Global configuration instance
_config: Optional[BillingSystemConfig] = None


def get_config() -> BillingSystemConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(env_file: Optional[str] = None) -> BillingSystemConfig:
    """Reload configuration (useful for testing)."""
    global _config
    _config = load_config(env_file)
    return _config
