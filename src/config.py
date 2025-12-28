"""Configuration management using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Idealista API configuration."""

    idealista_api_key: str = Field(..., description="Idealista API key")
    idealista_api_secret: str = Field(..., description="Idealista API secret")
    target_country: str = Field(default="es", description="Target country code")
    target_location_id: str = Field(default="0-EU-ES-28", description="Target location ID (Madrid)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    database_url: str = Field(..., description="PostgreSQL connection string")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class StorageSettings(BaseSettings):
    """Google Cloud Storage configuration."""

    gcs_bucket_name: str = Field(..., description="GCS bucket name for raw responses")
    google_cloud_project: str = Field(default="", description="GCP project ID")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class JobSettings(BaseSettings):
    """Job execution configuration."""

    job_type: str = Field(default="daily_new_listings", description="Type of job to run")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class Settings:
    """Global settings container."""

    def __init__(self):
        self.api = ApiSettings()
        self.database = DatabaseSettings()
        self.storage = StorageSettings()
        self.job = JobSettings()


# Global settings instance
settings = Settings()
