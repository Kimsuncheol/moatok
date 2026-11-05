"""Domain models and validation for collected content and shareable messages.

IMPORTANT ARCHITECTURAL NOTE:
This backend does NOT automatically post messages to KakaoTalk Open Chat rooms.
Instead, it collects/curates content, builds a structured shareable message
payload (`kakao_share_payload`), stores it in Cloud Firestore, and sends a
Firebase Cloud Messaging (FCM) push notification to the user's Flutter app.
The user then initiates the actual KakaoTalk sharing action from the Flutter app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


VALID_MESSAGE_STATUSES = {"ready_to_share", "notified", "shared_by_user", "archived"}


class ValidationError(ValueError):
    """Raised when incoming request payload fails validation."""


@dataclass
class SourceContentItem:
    """A single collected content item (e.g., article, link, or note)."""

    title: str
    url: str | None = None
    summary: str | None = None
    source_name: str | None = None
    image_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceContentItem:
        if not isinstance(data, dict):
            raise ValidationError("Each content item must be a JSON object.")
        title = str(data.get("title") or "").strip()
        if not title:
            raise ValidationError("Content item 'title' is required.")
        url = str(data["url"]).strip() if data.get("url") else None
        summary = str(data["summary"]).strip() if data.get("summary") else None
        source_name = (
            str(data["source_name"]).strip() if data.get("source_name") else None
        )
        image_url = str(data["image_url"]).strip() if data.get("image_url") else None
        return cls(
            title=title,
            url=url,
            summary=summary,
            source_name=source_name,
            image_url=image_url,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source_name": self.source_name,
            "image_url": self.image_url,
        }


@dataclass
class ShareableMessage:
    """Prepared message stored in Firestore for user-initiated KakaoTalk sharing in Flutter."""

    user_id: str
    title: str
    items: list[SourceContentItem]
    formatted_text: str
    kakao_share_payload: dict[str, Any]
    target_audience_hint: str | None = None
    tags: list[str] = field(default_factory=list)
    status: str = "ready_to_share"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_notified_at: str | None = None
    shared_by_user_at: str | None = None
    message_id: str | None = None

    def to_firestore_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "title": self.title,
            "items": [item.to_dict() for item in self.items],
            "formatted_text": self.formatted_text,
            "kakao_share_payload": self.kakao_share_payload,
            "target_audience_hint": self.target_audience_hint,
            "tags": self.tags,
            "status": self.status,
            "sharing_mode": "user_initiated_flutter",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_notified_at": self.last_notified_at,
            "shared_by_user_at": self.shared_by_user_at,
        }

    def to_api_dict(self) -> dict[str, Any]:
        payload = self.to_firestore_dict()
        if self.message_id:
            payload["id"] = self.message_id
        return payload
