"""Firestore repository for the `articles` collection."""

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
    generate_article_id,
    normalize_url,
    utc_now,
)


class ArticleRepository:
    """Repository managing collected articles in the `articles` collection.

    Uses deterministic document IDs derived from normalized `canonical_url`
    together with Firestore transactions so repeated or concurrent collection
    jobs never create duplicate articles.
    """

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
            return current_app.config.get("FIRESTORE_COLLECTION_ARTICLES", "articles")
        return "articles"

    def _collection(self) -> Any:
        return self.db.collection(self.collection_name)

    @staticmethod
    def _to_record(doc_id: str, data: Mapping[str, Any]) -> RecordDict:
        record = RecordDict(data)
        record["id"] = doc_id
        return record

    def _build_document(
        self,
        *,
        source_id: str,
        source_url: str,
        canonical_url: str,
        title: str,
        summary: str | None = None,
        published_at: datetime | str | None = None,
        collected_at: datetime | str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if extra:
            assert_no_forbidden_secrets(extra)

        cleaned_source_id = str(source_id or "").strip()
        if not cleaned_source_id:
            raise ValidationError("Article 'source_id' is required.")

        normalized_source_url = normalize_url(source_url, field_name="source_url")
        normalized_canonical_url = normalize_url(
            canonical_url, field_name="canonical_url"
        )

        cleaned_title = str(title or "").strip()
        if not cleaned_title:
            raise ValidationError("Article 'title' is required.")

        cleaned_summary = str(summary).strip() if summary is not None else ""

        utc_published = ensure_utc_datetime(
            published_at,
            field_name="published_at",
            allow_none=True,
        )
        utc_collected = (
            ensure_utc_datetime(
                collected_at,
                field_name="collected_at",
                allow_none=False,
            )
            if collected_at is not None
            else utc_now()
        )

        doc = {
            "source_id": cleaned_source_id,
            "source_url": normalized_source_url,
            "canonical_url": normalized_canonical_url,
            "title": cleaned_title,
            "summary": cleaned_summary,
            "published_at": utc_published,
            "collected_at": utc_collected,
        }
        assert_no_forbidden_secrets(doc)
        return doc

    def create_or_get_with_status(
        self,
        data: Mapping[str, Any] | None = None,
        *,
        source_id: str | None = None,
        source_url: str | None = None,
        canonical_url: str | None = None,
        stable_id: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        published_at: datetime | str | None = None,
        publication_time: datetime | str | None = None,
        collected_at: datetime | str | None = None,
        collection_time: datetime | str | None = None,
    ) -> tuple[RecordDict, bool]:
        """Atomically create an article using its deterministic ID or return existing.

        Returns:
            Tuple of (article_record, created_bool).
        """
        raw: dict[str, Any] = dict(data) if data is not None else {}
        assert_no_forbidden_secrets(raw)

        resolved_source_id = (
            source_id if source_id is not None else raw.get("source_id", "")
        )
        resolved_source_url = (
            source_url if source_url is not None else raw.get("source_url", "")
        )
        resolved_canonical_url = (
            canonical_url
            if canonical_url is not None
            else raw.get("canonical_url", "")
        )
        resolved_stable_id = (
            stable_id
            if stable_id is not None
            else raw.get("stable_id", raw.get("guid"))
        )
        resolved_title = title if title is not None else raw.get("title", "")
        resolved_summary = (
            summary if summary is not None else raw.get("summary", "")
        )
        resolved_published = (
            published_at
            if published_at is not None
            else (
                publication_time
                if publication_time is not None
                else raw.get("published_at", raw.get("publication_time"))
            )
        )
        resolved_collected = (
            collected_at
            if collected_at is not None
            else (
                collection_time
                if collection_time is not None
                else raw.get("collected_at", raw.get("collection_time"))
            )
        )

        doc_data = self._build_document(
            source_id=resolved_source_id,
            source_url=resolved_source_url,
            canonical_url=resolved_canonical_url,
            title=resolved_title,
            summary=resolved_summary,
            published_at=resolved_published,
            collected_at=resolved_collected,
            extra=raw,
        )
        if resolved_stable_id is not None and str(resolved_stable_id).strip():
            doc_data["stable_id"] = str(resolved_stable_id).strip()

        deterministic_id = generate_article_id(
            doc_data["canonical_url"],
            stable_id=doc_data.get("stable_id"),
            source_id=doc_data["source_id"],
        )
        canonical_doc_id = generate_article_id(doc_data["canonical_url"])
        doc_ref = self._collection().document(deterministic_id)
        canonical_ref = (
            self._collection().document(canonical_doc_id)
            if canonical_doc_id != deterministic_id
            else None
        )

        @firestore.transactional
        def _txn_create(transaction: Any) -> tuple[RecordDict, bool]:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                existing = snapshot.to_dict() or {}
                return self._to_record(snapshot.id, existing), False
            if canonical_ref is not None:
                canonical_snap = canonical_ref.get(transaction=transaction)
                if canonical_snap.exists:
                    existing = canonical_snap.to_dict() or {}
                    return self._to_record(canonical_snap.id, existing), False
            transaction.create(doc_ref, doc_data)
            return self._to_record(deterministic_id, doc_data), True

        transaction = self.db.transaction()
        return _txn_create(transaction)

    def create(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> RecordDict:
        """Create an article (or return the existing article if canonical_url was already collected)."""
        record, _ = self.create_or_get_with_status(data, **kwargs)
        return record

    create_or_get = create
    save = create

    def get(self, article_id: str) -> RecordDict | None:
        """Retrieve an article by its document ID."""
        cleaned_id = (article_id or "").strip()
        if not cleaned_id:
            return None
        doc = self._collection().document(cleaned_id).get()
        if not doc.exists:
            return None
        return self._to_record(doc.id, doc.to_dict() or {})

    get_by_id = get

    def get_by_canonical_url(self, canonical_url: str) -> RecordDict | None:
        """Retrieve an article by its canonical URL using deterministic ID resolution."""
        deterministic_id = generate_article_id(canonical_url)
        return self.get(deterministic_id)

    def list_articles(
        self,
        *,
        source_id: str | None = None,
        limit: int = 50,
    ) -> list[RecordDict]:
        """List articles, optionally filtered by `source_id`."""
        query: Any = self._collection()
        if source_id:
            query = query.where("source_id", "==", source_id.strip())

        docs = query.limit(max(1, min(limit, 500))).stream()
        results = [self._to_record(doc.id, doc.to_dict() or {}) for doc in docs]
        results.sort(
            key=lambda item: item.get("collected_at") or datetime.min,
            reverse=True,
        )
        return results

    def list_by_source(self, source_id: str, limit: int = 50) -> list[RecordDict]:
        """List articles collected from a specific source."""
        return self.list_articles(source_id=source_id, limit=limit)
