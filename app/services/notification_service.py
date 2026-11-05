"""Service for managing user FCM device tokens and sending push notifications via FCM.

Important Architectural Principle:
Sending an FCM push notification only alerts the user's Flutter device that a
pending share message is ready to review. Notification attempts are tracked
observably in Firestore, but are NEVER treated as proof that the message was
shared to KakaoTalk.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
import logging
from typing import Any

from firebase_admin import exceptions as firebase_exceptions
from firebase_admin import messaging
from flask import current_app, has_app_context

from app.extensions import get_firestore_client
from app.models import ValidationError
from app.repositories.devices_repo import UserDeviceRepository
from app.repositories.share_messages_repo import ShareMessageRepository

logger = logging.getLogger(__name__)

CONCISE_NOTIFICATION_TITLE = "카카오톡 공유 준비 완료"
CONCISE_NOTIFICATION_BODY = "새 공유 메시지가 준비되었습니다. 앱에서 확인 후 공유해보세요."


def is_invalid_or_expired_fcm_error(exc: Exception) -> bool:
    """Return True if the FCM exception indicates an invalid, expired, or unregistered device token."""
    if isinstance(
        exc,
        (
            messaging.UnregisteredError,
            messaging.SenderIdMismatchError,
            firebase_exceptions.InvalidArgumentError,
            firebase_exceptions.NotFoundError,
        ),
    ):
        return True

    code = str(getattr(exc, "code", "") or "").lower()
    msg = str(exc or "").lower()
    invalid_markers = (
        "unregistered",
        "registration-token-not-registered",
        "invalid-registration-token",
        "invalid-argument",
        "invalid_argument",
        "invalid token",
        "expired",
        "not-found",
    )
    return any(marker in code or marker in msg for marker in invalid_markers)


def build_concise_fcm_message(
    *,
    share_message_id: str,
    token: str,
) -> messaging.Message:
    """Build a concise FCM Message containing only the share message ID and non-sensitive routing metadata.

    Never includes sensitive user information, credentials, tokens, or full article contents.
    """
    cleaned_id = str(share_message_id or "").strip()
    if not cleaned_id:
        raise ValidationError("'share_message_id' is required to build an FCM notification.")

    data_payload = {
        "action": "OPEN_SHARE_PREVIEW",
        "share_message_id": cleaned_id,
        "message_id": cleaned_id,
        "sharing_mode": "user_initiated_flutter",
    }

    return messaging.Message(
        notification=messaging.Notification(
            title=CONCISE_NOTIFICATION_TITLE,
            body=CONCISE_NOTIFICATION_BODY,
        ),
        data=data_payload,
        token=token,
    )


def register_user_fcm_token(
    user_id: str,
    fcm_token: str,
    platform: str = "flutter",
    device_id: str | None = None,
) -> dict[str, Any]:
    """Register or update a user's FCM device token in `users/{userId}/devices`."""
    cleaned_token = (fcm_token or "").strip()
    if not cleaned_token:
        raise ValidationError("'fcm_token' is required.")

    cleaned_platform = (platform or "flutter").strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()

    device_repo = UserDeviceRepository()
    device_record = device_repo.upsert_device(
        user_id=user_id,
        device_id=device_id,
        fcm_token=cleaned_token,
        platform=cleaned_platform,
        enabled=True,
    )
    active_devices = device_repo.list_devices(user_id=user_id, enabled_only=True)
    tokens = [d["fcm_token"] for d in active_devices if d.get("fcm_token")]

    db = get_firestore_client()
    users_collection = (
        current_app.config["FIRESTORE_COLLECTION_USERS"]
        if has_app_context()
        else "users"
    )
    user_ref = db.collection(users_collection).document(user_id)
    user_ref.set(
        {
            "user_id": user_id,
            "fcm_tokens": tokens,
            "last_platform": cleaned_platform,
            "updated_at": now_iso,
        },
        merge=True,
    )

    return {
        "user_id": user_id,
        "device_id": device_record["device_id"],
        "token_count": len(tokens),
        "platform": cleaned_platform,
        "enabled": True,
        "updated_at": now_iso,
    }


def _deactivate_invalid_user_token(
    user_id: str,
    token: str,
    *,
    device_id: str | None = None,
    device_repo: UserDeviceRepository | None = None,
) -> list[str]:
    """Deactivate any device in `users/{userId}/devices` matching `device_id` or `token`."""
    repo = device_repo or UserDeviceRepository()
    deactivated_ids: list[str] = []

    if device_id:
        updated = repo.deactivate_device(user_id, device_id)
        if updated:
            deactivated_ids.append(device_id)
    else:
        for dev in repo.list_devices(user_id, enabled_only=True):
            if dev.get("fcm_token") == token:
                dev_id = str(dev["device_id"])
                repo.deactivate_device(user_id, dev_id)
                deactivated_ids.append(dev_id)

    db = repo.db
    users_collection = repo.users_collection_name
    user_ref = db.collection(users_collection).document(user_id)
    doc = user_ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        remaining = [
            str(t)
            for t in (data.get("fcm_tokens") or [])
            if str(t).strip() and str(t).strip() != token
        ]
        user_ref.update({"fcm_tokens": remaining})

    return deactivated_ids


def get_user_fcm_tokens(user_id: str) -> list[str]:
    """Retrieve active registered FCM tokens for a user from `users/{userId}/devices`."""
    device_repo = UserDeviceRepository()
    devices = device_repo.list_devices(user_id=user_id, enabled_only=True)
    subcollection_tokens = [
        str(d["fcm_token"]).strip()
        for d in devices
        if str(d.get("fcm_token") or "").strip()
    ]
    if subcollection_tokens:
        return list(dict.fromkeys(subcollection_tokens))

    db = get_firestore_client()
    users_collection = (
        current_app.config["FIRESTORE_COLLECTION_USERS"]
        if has_app_context()
        else "users"
    )
    doc = db.collection(users_collection).document(user_id).get()
    if not doc.exists:
        return []
    data = doc.to_dict() or {}
    return [str(t) for t in (data.get("fcm_tokens") or []) if str(t).strip()]


def notify_pending_share_message(
    share_message: Mapping[str, Any] | str,
    *,
    user_id: str | None = None,
    target_user_ids: Iterable[str] | None = None,
    share_repo: ShareMessageRepository | None = None,
    device_repo: UserDeviceRepository | None = None,
) -> dict[str, Any]:
    """Send concise FCM notifications for a pending share message and record observable telemetry.

    Important:
    - Sends only the share message ID and action metadata (no sensitive content).
    - Deactivates invalid or expired device tokens upon FCM error.
    - Records notification attempt metadata without marking the message as shared to KakaoTalk.
    """
    s_repo = share_repo or ShareMessageRepository()
    d_repo = device_repo or UserDeviceRepository(db=s_repo.db)

    if isinstance(share_message, str):
        record = s_repo.get(share_message)
        if not record:
            raise ValidationError(f"Share message '{share_message}' not found.")
    elif isinstance(share_message, Mapping):
        msg_id = str(share_message.get("id") or "").strip()
        if not msg_id:
            raise ValidationError("Share message 'id' is required.")
        record = s_repo.get(msg_id) or dict(share_message)
    else:
        raise ValidationError("Invalid share_message argument.")

    share_message_id = str(record.get("id") or "").strip()

    resolved_user_ids: list[str] = []
    if user_id:
        resolved_user_ids.append(user_id.strip())
    if target_user_ids:
        for uid in target_user_ids:
            cleaned_uid = str(uid or "").strip()
            if cleaned_uid and cleaned_uid not in resolved_user_ids:
                resolved_user_ids.append(cleaned_uid)

    if not resolved_user_ids and record.get("user_id"):
        resolved_user_ids.append(str(record["user_id"]).strip())

    # Collect active (user_id, device_id, token) targets
    targets: list[tuple[str, str | None, str]] = []
    for uid in resolved_user_ids:
        active_devices = d_repo.list_devices(uid, enabled_only=True)
        if active_devices:
            for dev in active_devices:
                tok = str(dev.get("fcm_token") or "").strip()
                if tok:
                    targets.append((uid, str(dev.get("device_id") or ""), tok))
        else:
            for tok in get_user_fcm_tokens(uid):
                targets.append((uid, None, tok))

    sent_count = 0
    failed_count = 0
    invalid_token_count = 0
    deactivated_device_ids: list[str] = []
    fcm_message_ids: list[str] = []

    for target_uid, dev_id, token in targets:
        fcm_message = build_concise_fcm_message(
            share_message_id=share_message_id,
            token=token,
        )
        try:
            resp_id = messaging.send(fcm_message)
            sent_count += 1
            fcm_message_ids.append(resp_id)
        except Exception as exc:
            failed_count += 1
            if is_invalid_or_expired_fcm_error(exc):
                invalid_token_count += 1
                deactivated = _deactivate_invalid_user_token(
                    target_uid,
                    token,
                    device_id=dev_id,
                    device_repo=d_repo,
                )
                deactivated_device_ids.extend(deactivated)
                logger.warning(
                    "Deactivated invalid/expired FCM device token (user_id=%s, device_id=%s, share_message_id=%s): %s",
                    target_uid,
                    dev_id or "unknown",
                    share_message_id,
                    exc.__class__.__name__,
                )
            else:
                logger.warning(
                    "FCM notification attempt failed (user_id=%s, device_id=%s, share_message_id=%s): %s",
                    target_uid,
                    dev_id or "unknown",
                    share_message_id,
                    exc.__class__.__name__,
                )

    updated_record = s_repo.record_notification_attempt(
        share_message_id,
        sent_count=sent_count,
        failed_count=failed_count,
        invalid_token_count=invalid_token_count,
    )

    notification_status = (
        updated_record["last_notification_status"]
        if updated_record
        else ("sent" if sent_count > 0 else ("failed" if failed_count > 0 else "no_registered_devices"))
    )
    attempts = (
        int(updated_record["notification_attempts"])
        if updated_record
        else 1
    )
    current_status = (
        str(updated_record["status"])
        if updated_record
        else str(record.get("status") or "pending")
    )

    result: dict[str, Any] = {
        "share_message_id": share_message_id,
        "message_id": share_message_id,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "invalid_token_count": invalid_token_count,
        "deactivated_device_ids": deactivated_device_ids,
        "fcm_message_ids": fcm_message_ids,
        "notification_status": notification_status,
        "notification_attempts": attempts,
        "share_message_status": current_status,
        "kakao_shared": False,
    }
    if not targets:
        result["reason"] = "no_registered_fcm_tokens"
    return result


def notify_user_message_ready(message_doc: dict[str, Any]) -> dict[str, Any]:
    """Send a concise FCM push notification prompting the user to open Flutter and share to KakaoTalk."""
    user_id = str(message_doc.get("user_id") or "")
    message_id = str(message_doc.get("id") or "")

    device_repo = UserDeviceRepository()
    active_devices = (
        device_repo.list_devices(user_id, enabled_only=True) if user_id else []
    )
    if active_devices:
        targets = [
            (str(d.get("device_id") or ""), str(d.get("fcm_token") or "").strip())
            for d in active_devices
            if str(d.get("fcm_token") or "").strip()
        ]
    else:
        targets = [(None, tok) for tok in get_user_fcm_tokens(user_id)]

    if not targets:
        return {
            "sent_count": 0,
            "failed_count": 0,
            "invalid_token_count": 0,
            "deactivated_device_ids": [],
            "reason": "no_registered_fcm_tokens",
            "kakao_shared": False,
        }

    sent_count = 0
    failed_count = 0
    invalid_token_count = 0
    deactivated_device_ids: list[str] = []
    message_ids: list[str] = []

    for dev_id, token in targets:
        fcm_message = build_concise_fcm_message(
            share_message_id=message_id,
            token=token,
        )
        try:
            resp_id = messaging.send(fcm_message)
            sent_count += 1
            message_ids.append(resp_id)
        except Exception as exc:
            failed_count += 1
            if is_invalid_or_expired_fcm_error(exc):
                invalid_token_count += 1
                deactivated = _deactivate_invalid_user_token(
                    user_id,
                    token,
                    device_id=dev_id,
                    device_repo=device_repo,
                )
                deactivated_device_ids.extend(deactivated)
                logger.warning(
                    "Deactivated invalid/expired FCM token for user_id=%s: %s",
                    user_id,
                    exc.__class__.__name__,
                )
            else:
                logger.warning(
                    "Failed to send FCM notification for user_id=%s: %s",
                    user_id,
                    exc.__class__.__name__,
                )

    if sent_count > 0 and message_id:
        now_iso = datetime.now(timezone.utc).isoformat()
        db = get_firestore_client()
        collection_name = (
            current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
            if has_app_context()
            else "shareable_messages"
        )
        doc_ref = db.collection(collection_name).document(message_id)
        if doc_ref.get().exists:
            doc_ref.update(
                {
                    "status": "notified",
                    "last_notified_at": now_iso,
                    "updated_at": now_iso,
                }
            )

    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "invalid_token_count": invalid_token_count,
        "deactivated_device_ids": deactivated_device_ids,
        "fcm_message_ids": message_ids,
        "kakao_shared": False,
    }
