"""Service for managing user FCM device tokens and sending push notifications via FCM.

When a shareable message is prepared in Firestore, this service notifies the
user's Flutter app so the user can open the prepared content and share it to
KakaoTalk themselves.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from firebase_admin import messaging
from flask import current_app

from app.extensions import get_firestore_client
from app.models import ValidationError

logger = logging.getLogger(__name__)


def register_user_fcm_token(
    user_id: str, fcm_token: str, platform: str = "flutter"
) -> dict[str, Any]:
    """Store or update a user's Firebase Cloud Messaging token in Cloud Firestore."""
    cleaned_token = (fcm_token or "").strip()
    if not cleaned_token:
        raise ValidationError("'fcm_token' is required.")

    cleaned_platform = (platform or "flutter").strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()

    db = get_firestore_client()
    users_collection = current_app.config["FIRESTORE_COLLECTION_USERS"]
    user_ref = db.collection(users_collection).document(user_id)
    doc = user_ref.get()

    existing_data = (doc.to_dict() or {}) if doc.exists else {}
    tokens: list[str] = list(existing_data.get("fcm_tokens") or [])
    if cleaned_token not in tokens:
        tokens.append(cleaned_token)

    record = {
        "user_id": user_id,
        "fcm_tokens": tokens,
        "last_platform": cleaned_platform,
        "updated_at": now_iso,
    }
    user_ref.set(record, merge=True)
    return {
        "user_id": user_id,
        "token_count": len(tokens),
        "platform": cleaned_platform,
        "updated_at": now_iso,
    }


def get_user_fcm_tokens(user_id: str) -> list[str]:
    """Retrieve registered FCM tokens for a user from Cloud Firestore."""
    db = get_firestore_client()
    users_collection = current_app.config["FIRESTORE_COLLECTION_USERS"]
    doc = db.collection(users_collection).document(user_id).get()
    if not doc.exists:
        return []
    data = doc.to_dict() or {}
    return [str(t) for t in (data.get("fcm_tokens") or []) if str(t).strip()]


def notify_user_message_ready(message_doc: dict[str, Any]) -> dict[str, Any]:
    """Send an FCM push notification prompting the user to open Flutter and share to KakaoTalk."""
    user_id = str(message_doc.get("user_id") or "")
    message_id = str(message_doc.get("id") or "")
    title = str(message_doc.get("title") or "새 공유 콘텐츠가 준비되었습니다")

    tokens = get_user_fcm_tokens(user_id)
    if not tokens:
        return {
            "sent_count": 0,
            "failed_count": 0,
            "reason": "no_registered_fcm_tokens",
        }

    notification_title = "카카오톡 공유 준비 완료"
    notification_body = f"'{title}' 메시지를 앱에서 확인하고 카카오톡으로 공유해보세요."

    data_payload = {
        "action": "OPEN_SHARE_PREVIEW",
        "message_id": message_id,
        "user_id": user_id,
        "sharing_mode": "user_initiated_flutter",
    }

    sent_count = 0
    failed_count = 0
    message_ids: list[str] = []

    for token in tokens:
        fcm_message = messaging.Message(
            notification=messaging.Notification(
                title=notification_title,
                body=notification_body,
            ),
            data=data_payload,
            token=token,
        )
        try:
            resp_id = messaging.send(fcm_message)
            sent_count += 1
            message_ids.append(resp_id)
        except Exception as exc:
            logger.warning("Failed to send FCM notification to token: %s", exc)
            failed_count += 1

    if sent_count > 0 and message_id:
        now_iso = datetime.now(timezone.utc).isoformat()
        db = get_firestore_client()
        collection_name = current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
        db.collection(collection_name).document(message_id).update(
            {
                "status": "notified",
                "last_notified_at": now_iso,
                "updated_at": now_iso,
            }
        )

    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "fcm_message_ids": message_ids,
    }
