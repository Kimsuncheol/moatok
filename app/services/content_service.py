"""Service for collecting content and preparing shareable messages in Cloud Firestore.

Note on KakaoTalk sharing:
This service never directly sends messages to KakaoTalk or Open Chat rooms.
It formats collected content into human-readable text and a structured payload
that the separate Flutter client app retrieves and passes to the user-initiated
KakaoTalk Share SDK / native share sheet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import current_app

from app.extensions import get_firestore_client
from app.models import (
    VALID_MESSAGE_STATUSES,
    ShareableMessage,
    SourceContentItem,
    ValidationError,
)
from app.repositories.share_messages_repo import ShareMessageRepository


def format_kakao_share_bundle(
    title: str,
    items: list[SourceContentItem],
    intro_note: str | None = None,
    button_title: str = "자세히 보기",
) -> tuple[str, dict[str, Any]]:
    """Build both plain formatted text and a Kakao Flutter SDK template-ready dictionary."""
    lines: list[str] = [f"📌 {title}"]
    if intro_note:
        lines.append(intro_note.strip())
    lines.append("")

    for idx, item in enumerate(items, start=1):
        source_prefix = f"[{item.source_name}] " if item.source_name else ""
        lines.append(f"{idx}. {source_prefix}{item.title}")
        if item.summary:
            lines.append(f"   - {item.summary}")
        if item.url:
            lines.append(f"   🔗 {item.url}")
        lines.append("")

    formatted_text = "\n".join(lines).strip()

    primary_item = items[0]
    primary_url = primary_item.url
    primary_image = next((i.image_url for i in items if i.image_url), None)

    # Structured payload consumed by the Flutter app to populate Kakao Share SDK
    # (FeedTemplate / TextTemplate) or clipboard/share sheet when the user taps "Share".
    kakao_share_payload: dict[str, Any] = {
        "template_type": "feed" if primary_image else "text",
        "title": title,
        "description": intro_note or (primary_item.summary or primary_item.title),
        "text": formatted_text,
        "image_url": primary_image,
        "primary_web_url": primary_url,
        "button_title": button_title,
        "item_count": len(items),
        "requires_user_action_in_flutter": True,
    }
    return formatted_text, kakao_share_payload


def create_shareable_message(
    payload: dict[str, Any], default_user_id: str | None = None
) -> dict[str, Any]:
    """Validate incoming content items, prepare shareable payload, and persist in Firestore."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    user_id = str(payload.get("user_id") or default_user_id or "").strip()
    if not user_id or user_id == "system":
        raise ValidationError(
            "A target 'user_id' is required when creating a shareable message."
        )

    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValidationError("'title' is required.")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("'items' must be a non-empty list of content items.")

    items = [SourceContentItem.from_dict(raw) for raw in raw_items]
    intro_note = (
        str(payload["intro_note"]).strip() if payload.get("intro_note") else None
    )
    target_audience_hint = (
        str(payload["target_audience_hint"]).strip()
        if payload.get("target_audience_hint")
        else None
    )

    raw_tags = payload.get("tags") or []
    if not isinstance(raw_tags, list):
        raise ValidationError("'tags' must be a list of strings.")
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]

    formatted_text, kakao_share_payload = format_kakao_share_bundle(
        title=title,
        items=items,
        intro_note=intro_note,
    )

    message = ShareableMessage(
        user_id=user_id,
        title=title,
        items=items,
        formatted_text=formatted_text,
        kakao_share_payload=kakao_share_payload,
        target_audience_hint=target_audience_hint,
        tags=tags,
    )

    db = get_firestore_client()
    collection_name = current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
    doc_ref = db.collection(collection_name).document()
    message.message_id = doc_ref.id
    doc_ref.set(message.to_firestore_dict())

    return message.to_api_dict()


def list_shareable_messages(
    user_id: str | None = None, status: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """List prepared shareable messages from Firestore (filtered by user_id when provided)."""
    if status and status not in VALID_MESSAGE_STATUSES:
        raise ValidationError(
            f"Invalid status '{status}'. Must be one of: {sorted(VALID_MESSAGE_STATUSES)}"
        )

    db = get_firestore_client()
    collection_name = current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
    query: Any = db.collection(collection_name)
    if user_id:
        query = query.where("user_id", "==", user_id)
    if status:
        query = query.where("status", "==", status)

    docs = query.limit(max(1, min(limit, 100))).stream()
    results: list[dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)

    results.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return results


def get_shareable_message(message_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    """Retrieve a single shareable message by ID, enforcing ownership if user_id is given."""
    db = get_firestore_client()
    collection_name = current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
    doc = db.collection(collection_name).document(message_id).get()
    if doc.exists:
        data = doc.to_dict() or {}
        if user_id and user_id != "system" and data.get("user_id") != user_id:
            return None
        data["id"] = doc.id
        return data

    share_repo = ShareMessageRepository(db=db)
    share_record = share_repo.get(message_id)
    if share_record is not None:
        return ShareMessageRepository.to_api_dict(share_record)

    return None


def record_user_share_event(
    message_id: str, user_id: str, share_channel: str = "kakaotalk_flutter_sdk"
) -> dict[str, Any] | None:
    """Record that the user initiated and completed KakaoTalk sharing in the Flutter app."""
    db = get_firestore_client()
    collection_name = current_app.config["FIRESTORE_COLLECTION_MESSAGES"]
    doc_ref = db.collection(collection_name).document(message_id)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        if data.get("user_id") != user_id:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        updates = {
            "status": "shared_by_user",
            "shared_by_user_at": now_iso,
            "updated_at": now_iso,
            "last_share_channel": share_channel,
        }
        doc_ref.update(updates)
        data.update(updates)
        data["id"] = doc.id
        return data

    share_repo = ShareMessageRepository(db=db)
    updated_share = share_repo.mark_shared_by_user(
        message_id=message_id,
        user_id=user_id,
        share_channel=share_channel,
    )
    if updated_share is not None:
        return ShareMessageRepository.to_api_dict(updated_share)

    return None
