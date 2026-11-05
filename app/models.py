"""Domain models and validation for sources, articles, share messages, and user devices.

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


VALID_MESSAGE_STATUSES = {
    "pending",
    "ready_to_share",
    "notified",
    "shared_by_user",
    "archived",
}


class ValidationError(ValueError):
    """Raised when incoming request or repository payload fails validation."""


@dataclass
class Source:
    """Content source stored in the `sources` Firestore collection."""

    name: str
    url: str
    source_type: str
    enabled: bool = True
    last_checked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: str | None = None

    @property
    def last_checked_time(self) -> datetime | None:
        return self.last_checked_at

    @property
    def creation_time(self) -> datetime:
        return self.created_at

    def to_firestore_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "source_type": self.source_type,
            "enabled": self.enabled,
            "last_checked_at": self.last_checked_at,
            "created_at": self.created_at,
        }


@dataclass
class Article:
    """Collected article stored in the `articles` Firestore collection."""

    source_id: str
    source_url: str
    canonical_url: str
    title: str
    summary: str = ""
    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    article_id: str | None = None

    @property
    def publication_time(self) -> datetime | None:
        return self.published_at

    @property
    def collection_time(self) -> datetime:
        return self.collected_at

    def to_firestore_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "summary": self.summary,
            "published_at": self.published_at,
            "collected_at": self.collected_at,
        }


@dataclass
class ShareMessageRecord:
    """Prepared share message stored in the `share_messages` Firestore collection."""

    article_id: str
    title: str
    body: str
    target_url: str
    status: str = "ready_to_share"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str | None = None

    @property
    def creation_time(self) -> datetime:
        return self.created_at

    @property
    def update_time(self) -> datetime:
        return self.updated_at

    def to_firestore_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "body": self.body,
            "target_url": self.target_url,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class UserDevice:
    """Registered client device stored in `users/{userId}/devices/{deviceId}`."""

    user_id: str
    device_id: str
    fcm_token: str
    platform: str = "flutter"
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_firestore_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "fcm_token": self.fcm_token,
            "platform": self.platform,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_seen_at": self.last_seen_at,
        }


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
