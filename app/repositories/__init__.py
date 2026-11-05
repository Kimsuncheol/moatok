"""Firestore repositories for Moatok collections:
- `sources`
- `articles`
- `share_messages`
- `users/{userId}/devices`
"""

from __future__ import annotations

from app.repositories.articles_repo import ArticleRepository
from app.repositories.devices_repo import UserDeviceRepository
from app.repositories.firestore_utils import (
    RecordDict,
    assert_no_forbidden_secrets,
    ensure_utc_datetime,
    generate_article_id,
    generate_device_id,
    generate_share_message_id,
    generate_source_id,
    normalize_url,
    utc_now,
)
from app.repositories.share_messages_repo import ShareMessageRepository
from app.repositories.sources_repo import SourceRepository

__all__ = [
    "ArticleRepository",
    "RecordDict",
    "ShareMessageRepository",
    "SourceRepository",
    "UserDeviceRepository",
    "assert_no_forbidden_secrets",
    "ensure_utc_datetime",
    "generate_article_id",
    "generate_device_id",
    "generate_share_message_id",
    "generate_source_id",
    "normalize_url",
    "utc_now",
]
