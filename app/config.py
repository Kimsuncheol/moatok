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

    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    SESSION_COOKIE_NAME = '__session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
    KAKAO_ADMIN_KEY = os.getenv('KAKAO_ADMIN_KEY')
    KAKAO_CLIENT_SECRET = os.getenv('KAKAO_CLIENT_SECRET')
    KAKAO_REDIRECT_URI = os.getenv('KAKAO_REDIRECT_URI')
    KAKAO_FRONTEND_ORIGIN = os.getenv('KAKAO_FRONTEND_ORIGIN', 'https://moatalk-e6fe1.web.app')

    # GCP / Firebase settings
    # Note: In deployed environments (Cloud Run, GKE, App Engine), Application Default
    # Credentials (ADC) are used automatically without requiring a JSON key file.
    GOOGLE_CLOUD_PROJECT: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")

    # Firestore collections
    FIRESTORE_COLLECTION_SOURCES: str = os.getenv(
        "FIRESTORE_COLLECTION_SOURCES", "sources"
    )
    FIRESTORE_COLLECTION_ARTICLES: str = os.getenv(
        "FIRESTORE_COLLECTION_ARTICLES", "articles"
    )
    FIRESTORE_COLLECTION_SHARE_MESSAGES: str = os.getenv(
        "FIRESTORE_COLLECTION_SHARE_MESSAGES", "share_messages"
    )
    FIRESTORE_COLLECTION_MESSAGES: str = os.getenv(
        "FIRESTORE_COLLECTION_MESSAGES", "shareable_messages"
    )
    FIRESTORE_COLLECTION_USERS: str = os.getenv(
        "FIRESTORE_COLLECTION_USERS", "users"
    )
    FIRESTORE_SUBCOLLECTION_DEVICES: str = os.getenv(
        "FIRESTORE_SUBCOLLECTION_DEVICES", "devices"
    )

    # Optional internal API key for scheduled jobs or content ingestion pipelines
    INTERNAL_INGEST_API_KEY: str | None = os.getenv("INTERNAL_INGEST_API_KEY")

    # Cloud Scheduler OIDC authentication settings for POST /internal/jobs/collect
    SCHEDULER_SERVICE_ACCOUNT_EMAIL: str | None = os.getenv(
        "SCHEDULER_SERVICE_ACCOUNT_EMAIL"
    )
    SCHEDULER_OIDC_AUDIENCE: str | None = os.getenv("SCHEDULER_OIDC_AUDIENCE")

    # Source URL validation & SSRF protection settings
    ALLOWED_SOURCE_DOMAINS: tuple[str, ...] = tuple(
        d.strip().lower()
        for d in os.getenv("ALLOWED_SOURCE_DOMAINS", "").split(",")
        if d.strip()
    )
    SOURCE_FETCH_TIMEOUT_SECONDS: float = float(
        os.getenv("SOURCE_FETCH_TIMEOUT_SECONDS", "5.0")
    )
    SOURCE_FETCH_MAX_BYTES: int = int(
        os.getenv("SOURCE_FETCH_MAX_BYTES", str(1024 * 1024))
    )
    SOURCE_FETCH_MAX_REDIRECTS: int = int(
        os.getenv("SOURCE_FETCH_MAX_REDIRECTS", "3")
    )

    ENGLISH_SCRAPER_URL = os.getenv("ENGLISH_SCRAPER_URL", "https://english-scrapper.onrender.com")
    ENGLISH_SCRAPER_ENABLED = os.getenv("ENGLISH_SCRAPER_ENABLED", "false").lower() == "true"

    # Rule-based share message generator settings
    SHARE_MESSAGE_PREFIX: str = os.getenv("SHARE_MESSAGE_PREFIX", "[모아톡 브리핑]")
    SHARE_MESSAGE_MAX_TITLE_LENGTH: int = int(
        os.getenv("SHARE_MESSAGE_MAX_TITLE_LENGTH", "100")
    )
    SHARE_MESSAGE_MAX_DESCRIPTION_LENGTH: int = int(
        os.getenv("SHARE_MESSAGE_MAX_DESCRIPTION_LENGTH", "160")
    )
    SHARE_MESSAGE_MAX_BODY_LENGTH: int = int(
        os.getenv("SHARE_MESSAGE_MAX_BODY_LENGTH", "500")
    )

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
    SCHEDULER_SERVICE_ACCOUNT_EMAIL = (
        "moatok-scheduler@test-moatok-project.iam.gserviceaccount.com"
    )
    SCHEDULER_OIDC_AUDIENCE = "https://moatok-backend-test.a.run.app/internal/jobs/collect"
    ALLOWED_SOURCE_DOMAINS = (
        "example.com",
        "*.example.com",
        "example.org",
        "*.example.org",
    )
    SOURCE_FETCH_TIMEOUT_SECONDS = 3.0
    SOURCE_FETCH_MAX_BYTES = 512 * 1024
    SOURCE_FETCH_MAX_REDIRECTS = 3


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
