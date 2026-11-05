"""Shared utilities for Firestore repositories: UTC timestamps, deterministic IDs, and secret guards."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.models import ValidationError

FIELD_ALIASES: dict[str, str] = {
    "creation_time": "created_at",
    "update_time": "updated_at",
    "last_checked_time": "last_checked_at",
    "publication_time": "published_at",
    "collection_time": "collected_at",
}

FORBIDDEN_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "kakao_access_token",
        "kakao_refresh_token",
        "kakao_token",
        "kakao_admin_key",
        "kakao_rest_api_key",
        "kakao_client_secret",
        "access_token",
        "refresh_token",
        "service_account",
        "service_account_key",
        "service_account_json",
        "private_key",
        "private_key_id",
        "client_secret",
    }
)

FORBIDDEN_SECRET_VALUE_MARKERS: tuple[str, ...] = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    '"type": "service_account"',
    '"type":"service_account"',
)


class RecordDict(dict[str, Any]):
    """Dictionary representation of a Firestore document with attribute and alias access."""

    def _resolve_key(self, key: str) -> str:
        if super().__contains__(key):
            return key
        mapped = FIELD_ALIASES.get(key)
        if mapped and super().__contains__(mapped):
            return mapped
        return key

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(self._resolve_key(key))

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(self._resolve_key(key), default)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return super().__contains__(key)
        return super().__contains__(self._resolve_key(key))

    def __getattr__(self, name: str) -> Any:
        resolved = self._resolve_key(name)
        if super().__contains__(resolved):
            return super().__getitem__(resolved)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc_datetime(
    value: datetime | str | None,
    *,
    field_name: str = "timestamp",
    allow_none: bool = False,
) -> datetime | None:
    """Normalize a datetime or ISO-8601 string into a timezone-aware UTC datetime."""
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"'{field_name}' is required and must be a UTC timestamp.")

    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            if allow_none:
                return None
            raise ValidationError(f"'{field_name}' cannot be an empty string.")
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValidationError(
                f"'{field_name}' must be a valid ISO-8601 timestamp or datetime."
            ) from exc
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    raise ValidationError(
        f"'{field_name}' must be a datetime object or ISO-8601 timestamp string."
    )


def normalize_url(url: str, *, field_name: str = "url") -> str:
    """Validate and canonicalize an HTTP(S) URL for deterministic hashing and storage."""
    if not isinstance(url, str) or not url.strip():
        raise ValidationError(f"'{field_name}' is required and must be a non-empty URL.")

    raw = url.strip()
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if scheme not in {"http", "https"} or not netloc:
        raise ValidationError(f"'{field_name}' must be a valid http:// or https:// URL.")

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Drop fragments (#...) as they do not identify distinct server resources
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def generate_source_id(url: str) -> str:
    """Generate a deterministic Firestore document ID for a content source from its URL."""
    normalized = normalize_url(url, field_name="url")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"src_{digest}"


def generate_article_id(
    canonical_url: str | None = None,
    *,
    stable_id: str | None = None,
    source_id: str | None = None,
) -> str:
    """Generate a deterministic Firestore document ID for an article.

    Prefers a source-provided `stable_id` (normalizing it if it is a URL, or
    scoping it to `source_id` if it is an opaque identifier), falling back to
    the normalized `canonical_url`.
    """
    if stable_id is not None and str(stable_id).strip():
        cleaned_stable = str(stable_id).strip()
        try:
            key = normalize_url(cleaned_stable, field_name="stable_id")
        except ValidationError:
            prefix = f"{source_id.strip()}:" if source_id and source_id.strip() else ""
            key = f"id:{prefix}{cleaned_stable}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return f"art_{digest}"

    normalized = normalize_url(str(canonical_url or ""), field_name="canonical_url")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"art_{digest}"


def generate_share_message_id(article_id: str) -> str:
    """Generate a deterministic Firestore document ID for a share message from its article ID."""
    cleaned = (article_id or "").strip()
    if not cleaned:
        raise ValidationError("'article_id' is required to generate a share message ID.")
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:24]
    return f"msg_{digest}"


def generate_device_id(fcm_token: str) -> str:
    """Generate a deterministic Firestore document ID for a user device from its FCM token."""
    cleaned = (fcm_token or "").strip()
    if not cleaned:
        raise ValidationError("'fcm_token' is required to generate a device ID.")
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:24]
    return f"dev_{digest}"


def assert_no_forbidden_secrets(payload: Any) -> None:
    """Ensure Kakao access tokens and service account keys are never written to Firestore."""
    if isinstance(payload, Mapping):
        if (
            str(payload.get("type") or "").strip().lower() == "service_account"
            and ("client_email" in payload or "private_key" in payload)
        ):
            raise ValidationError(
                "Storing service account key material in Firestore is prohibited."
            )
        for key, value in payload.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in FORBIDDEN_SECRET_KEYS:
                raise ValidationError(
                    f"Storing secret or token field '{key}' in Firestore is prohibited."
                )
            assert_no_forbidden_secrets(value)
    elif isinstance(payload, (list, tuple, set)):
        for item in payload:
            assert_no_forbidden_secrets(item)
    elif isinstance(payload, str):
        for marker in FORBIDDEN_SECRET_VALUE_MARKERS:
            if marker in payload:
                raise ValidationError(
                    "Storing private keys or service account credentials in Firestore is prohibited."
                )
