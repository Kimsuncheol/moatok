"""Service layer for managing content sources, URL security validation, and connector probing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models import ValidationError
from app.repositories.firestore_utils import assert_no_forbidden_secrets
from app.repositories.sources_repo import SourceRepository
from app.services.source_connectors import (
    get_source_connector,
    get_supported_source_types,
)


def create_source_entry(
    payload: Mapping[str, Any],
    *,
    repo: SourceRepository | None = None,
) -> tuple[dict[str, Any], bool]:
    """Validate source configuration and URL (including redirects), then persist in Firestore."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    assert_no_forbidden_secrets(payload)

    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValidationError("Source 'name' is required.")

    raw_url = str(payload.get("url") or "").strip()
    if not raw_url:
        raise ValidationError("Source 'url' is required.")

    raw_type = str(payload.get("source_type") or "").strip().lower()
    if not raw_type:
        raise ValidationError("Source 'source_type' is required.")

    connector = get_source_connector(raw_type)

    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValidationError("Source 'enabled' must be a boolean.")

    probe = connector.fetch(raw_url)

    repository = repo or SourceRepository()
    record, created = repository.create_or_get_with_status(
        name=name,
        url=probe.final_url,
        source_type=connector.source_type,
        enabled=enabled,
    )
    return SourceRepository.to_api_dict(record), created


def list_source_entries(
    *,
    enabled_only: bool = False,
    source_type: str | None = None,
    limit: int = 100,
    repo: SourceRepository | None = None,
) -> list[dict[str, Any]]:
    """List configured content sources with optional filtering."""
    canonical_type: str | None = None
    if source_type is not None and str(source_type).strip():
        connector = get_source_connector(str(source_type).strip())
        canonical_type = connector.source_type

    repository = repo or SourceRepository()
    records = repository.list_sources(enabled_only=enabled_only, limit=limit)
    if canonical_type:
        records = [r for r in records if r.get("source_type") == canonical_type]
    return [SourceRepository.to_api_dict(r) for r in records]


def get_source_entry(
    source_id: str,
    *,
    repo: SourceRepository | None = None,
) -> dict[str, Any] | None:
    """Retrieve a single content source by ID."""
    repository = repo or SourceRepository()
    record = repository.get(source_id)
    if not record:
        return None
    return SourceRepository.to_api_dict(record)


def update_source_entry(
    source_id: str,
    payload: Mapping[str, Any],
    *,
    repo: SourceRepository | None = None,
) -> dict[str, Any] | None:
    """Validate and update a content source's fields (`name`, `url`, `source_type`, `enabled`)."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    assert_no_forbidden_secrets(payload)

    repository = repo or SourceRepository()
    existing = repository.get(source_id)
    if not existing:
        return None

    updates: dict[str, Any] = {}

    if "name" in payload:
        cleaned_name = str(payload.get("name") or "").strip()
        if not cleaned_name:
            raise ValidationError("Source 'name' cannot be empty.")
        updates["name"] = cleaned_name

    target_type = existing["source_type"]
    if "source_type" in payload:
        raw_type = str(payload.get("source_type") or "").strip().lower()
        if not raw_type:
            raise ValidationError("Source 'source_type' cannot be empty.")
        connector = get_source_connector(raw_type)
        target_type = connector.source_type
        updates["source_type"] = target_type
    else:
        connector = get_source_connector(target_type)

    if "url" in payload:
        raw_url = str(payload.get("url") or "").strip()
        if not raw_url:
            raise ValidationError("Source 'url' cannot be empty.")
        probe = connector.fetch(raw_url)
        updates["url"] = probe.final_url
    elif "source_type" in payload:
        # Re-validate existing URL against the new connector type
        probe = connector.fetch(existing["url"])
        updates["url"] = probe.final_url

    if "enabled" in payload:
        if not isinstance(payload["enabled"], bool):
            raise ValidationError("Source 'enabled' must be a boolean.")
        updates["enabled"] = payload["enabled"]

    if not updates:
        raise ValidationError(
            "At least one updatable field ('name', 'url', 'source_type', 'enabled') is required."
        )

    updated = repository.update(source_id, updates)
    if not updated:
        return None
    return SourceRepository.to_api_dict(updated)


def set_source_enabled_state(
    source_id: str,
    enabled: bool,
    *,
    repo: SourceRepository | None = None,
) -> dict[str, Any] | None:
    """Enable or disable a content source by ID."""
    repository = repo or SourceRepository()
    updated = repository.set_enabled(source_id, enabled=enabled)
    if not updated:
        return None
    return SourceRepository.to_api_dict(updated)


__all__ = [
    "create_source_entry",
    "get_source_entry",
    "get_supported_source_types",
    "list_source_entries",
    "set_source_enabled_state",
    "update_source_entry",
]
