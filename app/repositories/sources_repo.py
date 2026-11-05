"""Firestore repository for the `sources` collection."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flask import current_app, has_app_context
from google.cloud import firestore

from app.extensions import get_firestore_client
from app.models import ValidationError
from app.repositories.firestore_utils import (
    RecordDict,
    assert_no_forbidden_secrets,
    ensure_utc_datetime,
    generate_source_id,
    normalize_url,
    utc_now,
)

VALID_SOURCE_TYPES: frozenset[str] = frozenset(
    {"rss", "atom", "web", "api", "newsletter", "webhook", "custom"}
)


class SourceRepository:
    """Repository managing content source documents in the `sources` collection."""

    def __init__(
        self,
        db: Any | None = None,
        collection_name: str | None = None,
    ) -> None:
        self._db = db
        self._collection_name = collection_name

    @property
    def db(self) -> Any:
        return self._db if self._db is not None else get_firestore_client()

    @property
    def collection_name(self) -> str:
        if self._collection_name:
            return self._collection_name
        if has_app_context():
            return current_app.config.get("FIRESTORE_COLLECTION_SOURCES", "sources")
        return "sources"

    def _collection(self) -> Any:
        return self.db.collection(self.collection_name)

    @staticmethod
    def _to_record(doc_id: str, data: Mapping[str, Any]) -> RecordDict:
        record = RecordDict(data)
        record["id"] = doc_id
        return record

    @staticmethod
    def to_api_dict(record: Mapping[str, Any]) -> dict[str, Any]:
        """Serialize a source record into a JSON-ready dictionary with ISO-8601 UTC timestamps."""
        created_at = record.get("created_at")
        last_checked_at = record.get("last_checked_at")
        return {
            "id": record.get("id"),
            "name": record.get("name"),
            "url": record.get("url"),
            "source_type": record.get("source_type"),
            "enabled": bool(record.get("enabled", True)),
            "last_checked_at": (
                last_checked_at.isoformat()
                if isinstance(last_checked_at, datetime)
                else last_checked_at
            ),
            "created_at": (
                created_at.isoformat()
                if isinstance(created_at, datetime)
                else created_at
            ),
        }

    def _build_document(
        self,
        *,
        name: str,
        url: str,
        source_type: str,
        enabled: bool = True,
        last_checked_at: datetime | str | None = None,
        created_at: datetime | str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if extra:
            assert_no_forbidden_secrets(extra)

        cleaned_name = str(name or "").strip()
        if not cleaned_name:
            raise ValidationError("Source 'name' is required.")

        normalized_url = normalize_url(url, field_name="url")

        cleaned_type = str(source_type or "").strip().lower()
        if not cleaned_type:
            raise ValidationError("Source 'source_type' is required.")

        if not isinstance(enabled, bool):
            raise ValidationError("Source 'enabled' must be a boolean.")

        utc_last_checked = ensure_utc_datetime(
            last_checked_at,
            field_name="last_checked_at",
            allow_none=True,
        )
        utc_created = (
            ensure_utc_datetime(created_at, field_name="created_at", allow_none=False)
            if created_at is not None
            else utc_now()
        )

        doc = {
            "name": cleaned_name,
            "url": normalized_url,
            "source_type": cleaned_type,
            "enabled": enabled,
            "last_checked_at": utc_last_checked,
            "created_at": utc_created,
        }
        assert_no_forbidden_secrets(doc)
        return doc

    def create_or_get_with_status(
        self,
        data: Mapping[str, Any] | None = None,
        *,
        source_id: str | None = None,
        name: str | None = None,
        url: str | None = None,
        source_type: str | None = None,
        enabled: bool = True,
        last_checked_at: datetime | str | None = None,
        last_checked_time: datetime | str | None = None,
        created_at: datetime | str | None = None,
        creation_time: datetime | str | None = None,
    ) -> tuple[RecordDict, bool]:
        """Idempotently create a source in a transaction or return the existing one.

        Returns:
            Tuple of (source_record, created_bool).
        """
        raw: dict[str, Any] = dict(data) if data is not None else {}
        assert_no_forbidden_secrets(raw)

        resolved_name = name if name is not None else raw.get("name", "")
        resolved_url = url if url is not None else raw.get("url", "")
        resolved_type = (
            source_type
            if source_type is not None
            else raw.get("source_type", "")
        )
        resolved_enabled = (
            raw["enabled"] if "enabled" in raw and data is not None else enabled
        )
        resolved_last_checked = (
            last_checked_at
            if last_checked_at is not None
            else (
                last_checked_time
                if last_checked_time is not None
                else raw.get("last_checked_at", raw.get("last_checked_time"))
            )
        )
        resolved_created = (
            created_at
            if created_at is not None
            else (
                creation_time
                if creation_time is not None
                else raw.get("created_at", raw.get("creation_time"))
            )
        )

        doc_data = self._build_document(
            name=resolved_name,
            url=resolved_url,
            source_type=resolved_type,
            enabled=resolved_enabled,
            last_checked_at=resolved_last_checked,
            created_at=resolved_created,
            extra=raw,
        )

        resolved_id = (
            str(source_id or raw.get("id") or raw.get("source_id") or "").strip()
            or generate_source_id(doc_data["url"])
        )
        doc_ref = self._collection().document(resolved_id)

        @firestore.transactional
        def _txn_create(transaction: Any) -> tuple[RecordDict, bool]:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                existing = snapshot.to_dict() or {}
                return self._to_record(snapshot.id, existing), False
            transaction.create(doc_ref, doc_data)
            return self._to_record(resolved_id, doc_data), True

        transaction = self.db.transaction()
        return _txn_create(transaction)

    def create(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> RecordDict:
        """Create a source (or return the existing source with the same deterministic ID)."""
        record, _ = self.create_or_get_with_status(data, **kwargs)
        return record

    create_or_get = create
    save = create

    def get(self, source_id: str) -> RecordDict | None:
        """Retrieve a source by its document ID."""
        cleaned_id = (source_id or "").strip()
        if not cleaned_id:
            return None
        doc = self._collection().document(cleaned_id).get()
        if not doc.exists:
            return None
        return self._to_record(doc.id, doc.to_dict() or {})

    get_by_id = get

    def list_sources(
        self, *, enabled_only: bool = False, limit: int = 100
    ) -> list[RecordDict]:
        """List sources, optionally filtering to enabled sources only."""
        query: Any = self._collection()
        if enabled_only:
            query = query.where("enabled", "==", True)

        docs = query.limit(max(1, min(limit, 500))).stream()
        results = [self._to_record(doc.id, doc.to_dict() or {}) for doc in docs]
        results.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=True,
        )
        return results

    list_all = list_sources

    def update_last_checked(
        self,
        source_id: str,
        checked_at: datetime | str | None = None,
    ) -> RecordDict | None:
        """Update the `last_checked_at` UTC timestamp for a source."""
        cleaned_id = (source_id or "").strip()
        if not cleaned_id:
            return None

        utc_checked = (
            ensure_utc_datetime(checked_at, field_name="last_checked_at")
            if checked_at is not None
            else utc_now()
        )
        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_update(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            updates = {"last_checked_at": utc_checked}
            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_update(self.db.transaction())

    def set_enabled(self, source_id: str, enabled: bool) -> RecordDict | None:
        """Enable or disable a source."""
        if not isinstance(enabled, bool):
            raise ValidationError("Source 'enabled' must be a boolean.")
        cleaned_id = (source_id or "").strip()
        if not cleaned_id:
            return None

        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_update(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            updates = {"enabled": enabled}
            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_update(self.db.transaction())

    def update(
        self,
        source_id: str,
        updates: Mapping[str, Any],
    ) -> RecordDict | None:
        """Atomically update mutable fields (`name`, `url`, `source_type`, `enabled`, `last_checked_at`) on a source."""
        cleaned_id = (source_id or "").strip()
        if not cleaned_id:
            return None

        assert_no_forbidden_secrets(updates)
        sanitized: dict[str, Any] = {}

        if "name" in updates:
            cleaned_name = str(updates.get("name") or "").strip()
            if not cleaned_name:
                raise ValidationError("Source 'name' cannot be empty.")
            sanitized["name"] = cleaned_name

        if "url" in updates:
            sanitized["url"] = normalize_url(str(updates.get("url") or ""), field_name="url")

        if "source_type" in updates:
            cleaned_type = str(updates.get("source_type") or "").strip().lower()
            if not cleaned_type:
                raise ValidationError("Source 'source_type' cannot be empty.")
            sanitized["source_type"] = cleaned_type

        if "enabled" in updates:
            if not isinstance(updates["enabled"], bool):
                raise ValidationError("Source 'enabled' must be a boolean.")
            sanitized["enabled"] = updates["enabled"]

        if "last_checked_at" in updates or "last_checked_time" in updates:
            raw_checked = updates.get(
                "last_checked_at", updates.get("last_checked_time")
            )
            sanitized["last_checked_at"] = ensure_utc_datetime(
                raw_checked,
                field_name="last_checked_at",
                allow_none=True,
            )

        if not sanitized:
            raise ValidationError(
                "At least one updatable field ('name', 'url', 'source_type', 'enabled', 'last_checked_at') is required."
            )

        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_update(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            transaction.update(doc_ref, sanitized)
            existing.update(sanitized)
            return self._to_record(snapshot.id, existing)

        return _txn_update(self.db.transaction())

    def delete(self, source_id: str) -> bool:
        """Delete a source by ID. Returns True if it existed and was deleted."""
        cleaned_id = (source_id or "").strip()
        if not cleaned_id:
            return False
        doc_ref = self._collection().document(cleaned_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False
        doc_ref.delete()
        return True
