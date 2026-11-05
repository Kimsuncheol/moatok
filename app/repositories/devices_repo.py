"""Firestore repository for the `users/{userId}/devices` subcollection."""

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
    generate_device_id,
    utc_now,
)


class UserDeviceRepository:
    """Repository managing user device records in `users/{userId}/devices`."""

    def __init__(
        self,
        db: Any | None = None,
        users_collection_name: str | None = None,
        devices_subcollection_name: str | None = None,
    ) -> None:
        self._db = db
        self._users_collection_name = users_collection_name
        self._devices_subcollection_name = devices_subcollection_name

    @property
    def db(self) -> Any:
        return self._db if self._db is not None else get_firestore_client()

    @property
    def users_collection_name(self) -> str:
        if self._users_collection_name:
            return self._users_collection_name
        if has_app_context():
            return current_app.config.get("FIRESTORE_COLLECTION_USERS", "users")
        return "users"

    @property
    def devices_subcollection_name(self) -> str:
        if self._devices_subcollection_name:
            return self._devices_subcollection_name
        if has_app_context():
            return current_app.config.get("FIRESTORE_SUBCOLLECTION_DEVICES", "devices")
        return "devices"

    def _validate_user_id(self, user_id: str) -> str:
        cleaned = str(user_id or "").strip()
        if not cleaned:
            raise ValidationError("'user_id' is required for user device operations.")
        return cleaned

    def _devices_collection(self, user_id: str) -> Any:
        cleaned_user_id = self._validate_user_id(user_id)
        return (
            self.db.collection(self.users_collection_name)
            .document(cleaned_user_id)
            .collection(self.devices_subcollection_name)
        )

    @staticmethod
    def _to_record(doc_id: str, data: Mapping[str, Any]) -> RecordDict:
        record = RecordDict(data)
        record["id"] = doc_id
        record.setdefault("device_id", doc_id)
        return record

    def upsert_device(
        self,
        user_id: str,
        data: Mapping[str, Any] | None = None,
        *,
        device_id: str | None = None,
        fcm_token: str | None = None,
        platform: str | None = None,
        enabled: bool = True,
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None,
        last_seen_at: datetime | str | None = None,
    ) -> RecordDict:
        """Atomically register or update a device in `users/{userId}/devices/{deviceId}`."""
        cleaned_user_id = self._validate_user_id(user_id)
        raw: dict[str, Any] = dict(data) if data is not None else {}
        assert_no_forbidden_secrets(raw)

        resolved_token = str(
            fcm_token if fcm_token is not None else raw.get("fcm_token", "")
        ).strip()
        if not resolved_token:
            raise ValidationError("Device 'fcm_token' is required.")

        resolved_platform = (
            str(
                platform
                if platform is not None
                else raw.get("platform") or "flutter"
            )
            .strip()
            .lower()
        )
        resolved_enabled = (
            raw["enabled"] if "enabled" in raw and data is not None else enabled
        )
        if not isinstance(resolved_enabled, bool):
            raise ValidationError("Device 'enabled' must be a boolean.")

        resolved_device_id = (
            str(device_id or raw.get("device_id") or raw.get("id") or "").strip()
            or generate_device_id(resolved_token)
        )

        now = utc_now()
        utc_created = (
            ensure_utc_datetime(
                created_at or raw.get("created_at") or raw.get("creation_time"),
                field_name="created_at",
            )
            if (
                created_at is not None
                or "created_at" in raw
                or "creation_time" in raw
            )
            else now
        )
        utc_updated = (
            ensure_utc_datetime(
                updated_at or raw.get("updated_at") or raw.get("update_time"),
                field_name="updated_at",
            )
            if (
                updated_at is not None
                or "updated_at" in raw
                or "update_time" in raw
            )
            else now
        )
        utc_last_seen = (
            ensure_utc_datetime(
                last_seen_at or raw.get("last_seen_at"),
                field_name="last_seen_at",
            )
            if (last_seen_at is not None or "last_seen_at" in raw)
            else utc_updated
        )

        doc_ref = self._devices_collection(cleaned_user_id).document(resolved_device_id)

        @firestore.transactional
        def _txn_upsert(transaction: Any) -> RecordDict:
            snapshot = doc_ref.get(transaction=transaction)
            if snapshot.exists:
                existing = snapshot.to_dict() or {}
                updates = {
                    "user_id": cleaned_user_id,
                    "device_id": resolved_device_id,
                    "fcm_token": resolved_token,
                    "platform": resolved_platform,
                    "enabled": resolved_enabled,
                    "updated_at": utc_updated,
                    "last_seen_at": utc_last_seen,
                }
                assert_no_forbidden_secrets(updates)
                transaction.update(doc_ref, updates)
                existing.update(updates)
                return self._to_record(resolved_device_id, existing)

            new_doc = {
                "user_id": cleaned_user_id,
                "device_id": resolved_device_id,
                "fcm_token": resolved_token,
                "platform": resolved_platform,
                "enabled": resolved_enabled,
                "created_at": utc_created,
                "updated_at": utc_updated,
                "last_seen_at": utc_last_seen,
            }
            assert_no_forbidden_secrets(new_doc)
            transaction.create(doc_ref, new_doc)
            return self._to_record(resolved_device_id, new_doc)

        return _txn_upsert(self.db.transaction())

    register_device = upsert_device
    save = upsert_device

    def get_device(self, user_id: str, device_id: str) -> RecordDict | None:
        """Retrieve a specific device document from `users/{userId}/devices/{deviceId}`."""
        cleaned_device_id = (device_id or "").strip()
        if not cleaned_device_id:
            return None
        doc = self._devices_collection(user_id).document(cleaned_device_id).get()
        if not doc.exists:
            return None
        return self._to_record(doc.id, doc.to_dict() or {})

    get = get_device

    def list_devices(
        self,
        user_id: str,
        *,
        enabled_only: bool = False,
        limit: int = 50,
    ) -> list[RecordDict]:
        """List registered devices for a user under `users/{userId}/devices`."""
        query: Any = self._devices_collection(user_id)
        if enabled_only:
            query = query.where("enabled", "==", True)

        docs = query.limit(max(1, min(limit, 200))).stream()
        results = [self._to_record(doc.id, doc.to_dict() or {}) for doc in docs]
        results.sort(
            key=lambda item: item.get("updated_at") or datetime.min,
            reverse=True,
        )
        return results

    list_for_user = list_devices

    def deactivate_device(self, user_id: str, device_id: str) -> RecordDict | None:
        """Disable a device in `users/{userId}/devices/{deviceId}`."""
        cleaned_device_id = (device_id or "").strip()
        if not cleaned_device_id:
            return None

        doc_ref = self._devices_collection(user_id).document(cleaned_device_id)
        now = utc_now()

        @firestore.transactional
        def _txn_deactivate(transaction: Any) -> RecordDict | None:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return None
            existing = snapshot.to_dict() or {}
            updates = {"enabled": False, "updated_at": now}
            transaction.update(doc_ref, updates)
            existing.update(updates)
            return self._to_record(snapshot.id, existing)

        return _txn_deactivate(self.db.transaction())

    def delete_device(self, user_id: str, device_id: str) -> bool:
        """Delete a device document from `users/{userId}/devices/{deviceId}`."""
        cleaned_device_id = (device_id or "").strip()
        if not cleaned_device_id:
            return False
        doc_ref = self._devices_collection(user_id).document(cleaned_device_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False
        doc_ref.delete()
        return True

    delete = delete_device
