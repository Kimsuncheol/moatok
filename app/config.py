"""Environment-based configuration for the Moatok backend."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration loaded from environment variables."""

    ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = False
    TESTING: bool = False

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    PORT: int = int(os.getenv("PORT", "8080"))

    # GCP / Firebase settings
    # Note: In deployed environments (Cloud Run, GKE, App Engine), Application Default
    # Credentials (ADC) are used automatically without requiring a JSON key file.
    GOOGLE_CLOUD_PROJECT: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")

    # Firestore collections
    FIRESTORE_COLLECTION_MESSAGES: str = os.getenv(
        "FIRESTORE_COLLECTION_MESSAGES", "shareable_messages"
    )
    FIRESTORE_COLLECTION_USERS: str = os.getenv(
        "FIRESTORE_COLLECTION_USERS", "users"
    )

    # Optional internal API key for scheduled jobs or content ingestion pipelines
    INTERNAL_INGEST_API_KEY: str | None = os.getenv("INTERNAL_INGEST_API_KEY")

    # CORS configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")


class DevelopmentConfig(Config):
    """Development configuration."""

    ENV = "development"
    DEBUG = True


class TestingConfig(Config):
    """Automated test configuration (uses mocked Firebase/Firestore services)."""

    ENV = "testing"
    TESTING = True
    GOOGLE_CLOUD_PROJECT = "test-moatok-project"
    INTERNAL_INGEST_API_KEY = "test-internal-key"


class ProductionConfig(Config):
    """Production configuration."""

    ENV = "production"
    DEBUG = False
    TESTING = False


CONFIG_BY_NAME: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> type[Config]:
    """Return the Config class matching the given environment name."""
    resolved = (env_name or os.getenv("FLASK_ENV", "production")).lower()
    return CONFIG_BY_NAME.get(resolved, ProductionConfig)
