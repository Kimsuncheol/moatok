"""Firestore repository for the `share_messages` collection."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from flask import current_app, has_app_context
from google.cloud import firestore

from app.extensions import get_firestore_client
from app.models import VALID_MESSAGE_STATUSES, ValidationError
from app.repositories.firestore_utils import (
    RecordDict,
    assert_no_forbidden_secrets,
    ensure_utc_datetime,
    generate_share_message_id,
    normalize_url,
    utc_now,
)


class ShareMessageRepository:
    """Repository managing prepared share messages in the `share_messages` collection.

    Uses deterministic document IDs derived from `article_id` together with
    Firestore transactions so concurrent or repeated formatting jobs never
    create duplicate share messages for the same article.
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
            return current_app.config.get(
                "FIRESTORE_COLLECTION_SHARE_MESSAGES", "share_messages"
            )
        return "share_messages"

    def _collection(self) -> Any:
        return self.db.collection(self.collection_name)

    @staticmethod
    def _to_record(doc_id: str, data: Mapping[str, Any]) -> RecordDict:
        record = RecordDict(data)
        record["id"] = doc_id
        return record

    @staticmethod
    def to_api_dict(record: Mapping[str, Any]) -> dict[str, Any]:
        """Serialize a share message record into a JSON-ready dictionary with ISO-8601 UTC timestamps."""
        created_at = record.get("created_at")
        updated_at = record.get("updated_at")
        last_attempt_at = record.get("last_notification_attempt_at")
        last_notified_at = record.get("last_notified_at")
        shared_at = record.get("shared_by_user_at")
        return {
            "id": record.get("id"),
            "article_id": record.get("article_id"),
            "title": record.get("title"),
            "body": record.get("body"),
            "target_url": record.get("target_url"),
            "status": record.get("status"),
            "notification_attempts": int(record.get("notification_attempts", 0)),
            "last_notification_status": record.get("last_notification_status"),
            "last_notification_attempt_at": (
                last_attempt_at.isoformat()
                if isinstance(last_attempt_at, datetime)
                else last_attempt_at
            ),
            "last_notified_at": (
                last_notified_at.isoformat()
                if isinstance(last_notified_at, datetime)
                else last_notified_at
            ),
            "kakao_shared": bool(record.get("kakao_shared", False)),
            "shared_by_user_id": record.get("shared_by_user_id"),
            "last_share_channel": record.get("last_share_channel"),
            "shared_by_user_at": (
                shared_at.isoformat() if isinstance(shared_at, datetime) else shared_at
            ),
            "created_at": (
                created_at.isoformat()
                if isinstance(created_at, datetime)
                else created_at
            ),
            "updated_at": (
                updated_at.isoformat()
                if isinstance(updated_at, datetime)
                else updated_at
            ),
        }

    def _build_document(
        self,
        *,
        article_id: str,
        title: str,
        body: str,
        target_url: str,
        status: str = "pending",
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if extra:
            assert_no_forbidden_secrets(extra)

        cleaned_article_id = str(article_id or "").strip()
        if not cleaned_article_id:
            raise ValidationError("Share message 'article_id' is required.")

        cleaned_title = str(title or "").strip()
        if not cleaned_title:
            raise ValidationError("Share message 'title' is required.")

        cleaned_body = str(body or "").strip()
        if not cleaned_body:
            raise ValidationError("Share message 'body' is required.")

        normalized_target_url = normalize_url(target_url, field_name="target_url")

        cleaned_status = str(status or "ready_to_share").strip()
        if cleaned_status not in VALID_MESSAGE_STATUSES:
            raise ValidationError(
                f"Invalid share message status '{cleaned_status}'. "
                f"Must be one of: {sorted(VALID_MESSAGE_STATUSES)}"
            )

        now = utc_now()
        utc_created = (
            ensure_utc_datetime(created_at, field_name="created_at", allow_none=False)
            if created_at is not None
            else now
        )
        utc_updated = (
            ensure_utc_datetime(updated_at, field_name="updated_at", allow_none=False)
            if updated_at is not None
            else utc_created
        )

        doc = {
            "article_id": cleaned_article_id,
            "title": cleaned_title,
            "body": cleaned_body,
            "target_url": normalized_target_url,
            "status": cleaned_status,
            "notification_attempts": 0,
            "last_notification_status": None,
            "last_notification_attempt_at": None,
            "last_notified_at": None,
            "kakao_shared": False,
            "shared_by_user_at": None,
            "created_at": utc_created,
            "updated_at": utc_updated,
        }
        assert_no_forbidden_secrets(doc)
        return doc

    def create_or_get_with_status(
        self,
        data: Mapping[str, Any] | None = None,
        *,
        article_id: str | None = None,
        title: str | None = None,
        body: str | None = None,
        target_url: str | None = None,
        status: str | None = None,
        created_at: datetime | str | None = None,
        creation_time: datetime | str | None = None,
        updated_at: datetime | str | None = None,
        update_time: datetime | str | None = None,
    ) -> tuple[RecordDict, bool]:
        """Atomically create a share message for an article in a transaction or return existing.

        Returns:
            Tuple of (share_message_record, created_bool).
        """
        raw: dict[str, Any] = dict(data) if data is not None else {}
        assert_no_forbidden_secrets(raw)

        resolved_article_id = (
            article_id if article_id is not None else raw.get("article_id", "")
        )
        resolved_title = title if title is not None else raw.get("title", "")
        resolved_body = body if body is not None else raw.get("body", "")
        resolved_target_url = (
            target_url if target_url is not None else raw.get("target_url", "")
        )
        resolved_status = (
            status
            if status is not None
            else raw.get("status", "pending")
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
        resolved_updated = (
            updated_at
            if updated_at is not None
            else (
                update_time
                if update_time is not None
                else raw.get("updated_at", raw.get("update_time"))
            )
        )

        doc_data = self._build_document(
            article_id=resolved_article_id,
            title=resolved_title,
            body=resolved_body,
            target_url=resolved_target_url,
            status=resolved_status,
            created_at=resolved_created,
            updated_at=resolved_updated,
            extra=raw,
        )

        deterministic_id = generate_share_message_id(doc_data["article_id"])
        doc_ref = self._collection().document(deterministic_id)

        @firestore.transactional
        def _txn_create(transaction: Any) -> tuple[RecordDict, bool]:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                existing = snapshot.to_dict() or {}
                return self._to_record(snapshot.id, existing), False
            transaction.create(doc_ref, doc_data)
            return self._to_record(deterministic_id, doc_data), True

        transaction = self.db.transaction()
        return _txn_create(transaction)

    def create(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> RecordDict:
        """Create a share message for an article (idempotent across repeated/concurrent runs)."""
        record, _ = self.create_or_get_with_status(data, **kwargs)
        return record

    create_or_get = create
    save = create

    def get(self, message_id: str) -> RecordDict | None:
        """Retrieve a share message by its document ID."""
        cleaned_id = (message_id or "").strip()
        if not cleaned_id:
            return None
        doc = self._collection().document(cleaned_id).get()
        if not doc.exists:
            return None
        return self._to_record(doc.id, doc.to_dict() or {})

    get_by_id = get

    def get_by_article_id(self, article_id: str) -> RecordDict | None:
        """Retrieve the share message for a given `article_id` via deterministic ID lookup."""
        deterministic_id = generate_share_message_id(article_id)
        return self.get(deterministic_id)

    def list_messages(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[RecordDict]:
        """List share messages, optionally filtered by `status`."""
        query: Any = self._collection()
        if status:
            cleaned_status = status.strip()
            if cleaned_status not in VALID_MESSAGE_STATUSES:
                raise ValidationError(
                    f"Invalid status '{cleaned_status}'. "
                    f"Must be one of: {sorted(VALID_MESSAGE_STATUSES)}"
                )
            query = query.where("status", "==", cleaned_status)

        docs = query.limit(max(1, min(limit, 500))).stream()
        results = [self._to_record(doc.id, doc.to_dict() or {}) for doc in docs]
        results.sort(
            key=lambda item: item.get("created_at") or datetime.min,
            reverse=True,
        )
        return results

    def update_status(
        self,
        message_id: str,
        status: str,
        updated_at: datetime | str | None = None,
    ) -> RecordDict | None:
        """Atomically update a share message's status and UTC `updated_at` timestamp."""
        cleaned_id = (message_id or "").strip()
        if not cleaned_id:
            return None

        cleaned_status = str(status or "").strip()
        if cleaned_status not in VALID_MESSAGE_STATUSES:
            raise ValidationError(
                f"Invalid share message status '{cleaned_status}'. "
                f"Must be one of: {sorted(VALID_MESSAGE_STATUSES)}"
            )

        utc_updated = (
            ensure_utc_datetime(updated_at, field_name="updated_at")
            if updated_at is not None
            else utc_now()
        )
        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_update(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            updates = {
                "status": cleaned_status,
                "updated_at": utc_updated,
            }
            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_update(self.db.transaction())

    def update_pending_message(
        self,
        message_id: str,
        updates: Mapping[str, Any],
        *,
        max_title_length: int | None = None,
        max_body_length: int | None = None,
    ) -> RecordDict | None:
        """Atomically edit a share message only when its current status is `'pending'`."""
        cleaned_id = (message_id or "").strip()
        if not cleaned_id:
            return None

        assert_no_forbidden_secrets(updates)
        sanitized: dict[str, Any] = {}

        if "title" in updates:
            cleaned_title = " ".join(str(updates.get("title") or "").split()).strip()
            if not cleaned_title:
                raise ValidationError("Share message 'title' cannot be empty.")
            if max_title_length is not None and len(cleaned_title) > max_title_length:
                raise ValidationError(
                    f"Share message 'title' exceeds maximum length of {max_title_length} characters."
                )
            sanitized["title"] = cleaned_title

        if "body" in updates:
            cleaned_body = str(updates.get("body") or "").strip()
            if not cleaned_body:
                raise ValidationError("Share message 'body' cannot be empty.")
            if max_body_length is not None and len(cleaned_body) > max_body_length:
                raise ValidationError(
                    f"Share message 'body' exceeds maximum length of {max_body_length} characters."
                )
            sanitized["body"] = cleaned_body

        if "target_url" in updates:
            sanitized["target_url"] = normalize_url(
                str(updates.get("target_url") or ""), field_name="target_url"
            )

        if "status" in updates:
            cleaned_status = str(updates.get("status") or "").strip()
            if cleaned_status not in VALID_MESSAGE_STATUSES:
                raise ValidationError(
                    f"Invalid share message status '{cleaned_status}'. "
                    f"Must be one of: {sorted(VALID_MESSAGE_STATUSES)}"
                )
            sanitized["status"] = cleaned_status

        if not sanitized:
            raise ValidationError(
                "At least one editable field ('title', 'body', 'target_url', 'status') is required."
            )

        sanitized["updated_at"] = utc_now()
        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_edit(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            if existing.get("status") != "pending":
                raise ValidationError(
                    f"Cannot edit share message in '{existing.get('status')}' status; only 'pending' messages can be edited."
                )
            transaction.update(doc_ref, sanitized)
            existing.update(sanitized)
            return self._to_record(snapshot.id, existing)

        return _txn_edit(self.db.transaction())

    def record_notification_attempt(
        self,
        message_id: str,
        *,
        sent_count: int,
        failed_count: int,
        invalid_token_count: int = 0,
        attempted_at: datetime | str | None = None,
    ) -> RecordDict | None:
        """Record an observable FCM notification attempt without marking the message as shared to KakaoTalk."""
        cleaned_id = (message_id or "").strip()
        if not cleaned_id:
            return None

        utc_attempted = (
            ensure_utc_datetime(attempted_at, field_name="attempted_at")
            if attempted_at is not None
            else utc_now()
        )

        if sent_count > 0 and failed_count == 0:
            attempt_status = "sent"
        elif sent_count > 0 and failed_count > 0:
            attempt_status = "partial_failure"
        elif sent_count == 0 and failed_count > 0:
            attempt_status = "failed"
        else:
            attempt_status = "no_registered_devices"

        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_record(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            attempts = int(existing.get("notification_attempts") or 0) + 1
            updates: dict[str, Any] = {
                "notification_attempts": attempts,
                "last_notification_attempt_at": utc_attempted,
                "last_notification_status": attempt_status,
                "last_notification_sent_count": int(sent_count),
                "last_notification_failed_count": int(failed_count),
                "last_notification_invalid_token_count": int(invalid_token_count),
                "kakao_shared": bool(existing.get("kakao_shared", False)),
                "updated_at": utc_attempted,
            }
            if sent_count > 0:
                updates["last_notified_at"] = utc_attempted

            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_record(self.db.transaction())

    def claim_initial_notification(self, message_id: str) -> bool:
        """Atomically claim initial notification dispatch for a pending share message.

        Prevents duplicate push notifications when concurrent or retried jobs
        process the same share message.
        """
        cleaned_id = (message_id or "").strip()
        if not cleaned_id:
            return False

        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_claim(transaction: Any) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
            existing = snapshot.to_dict() or {}
            if (
                existing.get("initial_notification_claimed")
                or int(existing.get("notification_attempts") or 0) > 0
                or existing.get("last_notified_at") is not None
            ):
                return False
            transaction.update(
                doc_ref,
                {
                    "initial_notification_claimed": True,
                    "updated_at": utc_now(),
                },
            )
            return True

        return _txn_claim(self.db.transaction())

    def mark_shared_by_user(
        self,
        message_id: str,
        user_id: str,
        share_channel: str = "kakaotalk_flutter_sdk",
    ) -> RecordDict | None:
        """Record that an authenticated user completed user-initiated KakaoTalk sharing in Flutter."""
        cleaned_id = (message_id or "").strip()
        cleaned_uid = (user_id or "").strip()
        if not cleaned_id or not cleaned_uid:
            return None

        now = utc_now()
        doc_ref = self._collection().document(cleaned_id)

        @firestore.transactional
        def _txn_mark_shared(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            updates: dict[str, Any] = {
                "status": "shared",
                "kakao_shared": True,
                "shared_by_user_id": cleaned_uid,
                "shared_by_user_at": now,
                "last_share_channel": (share_channel or "kakaotalk_flutter_sdk").strip(),
                "updated_at": now,
            }
            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_mark_shared(self.db.transaction())
