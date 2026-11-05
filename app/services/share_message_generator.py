"""Rule-based share message generator for collected articles.

Strictly formats article metadata (configurable prefix, title, short description
when available, and original article URL) without inventing facts or copying
full article text, enforces configurable length limits, and stores messages in
`share_messages` with an initial `pending` status.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import current_app, has_app_context

from app.models import ValidationError
from app.repositories.firestore_utils import (
    RecordDict,
    assert_no_forbidden_secrets,
    normalize_url,
)
from app.repositories.share_messages_repo import ShareMessageRepository


def _collapse_whitespace(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def truncate_text(text: str, max_length: int) -> str:
    """Deterministically truncate text to at most `max_length` characters without inventing content."""
    if max_length <= 0:
        raise ValidationError("Length limit must be a positive integer.")
    cleaned = _collapse_whitespace(text)
    if len(cleaned) <= max_length:
        return cleaned
    if max_length <= 3:
        return cleaned[:max_length]
    return cleaned[: max_length - 3].rstrip() + "..."


def _get_default_prefix() -> str:
    if has_app_context():
        return str(current_app.config.get("SHARE_MESSAGE_PREFIX", "[모아톡 브리핑]")).strip()
    return "[모아톡 브리핑]"


def _get_default_max_title_length() -> int:
    if has_app_context():
        return int(current_app.config.get("SHARE_MESSAGE_MAX_TITLE_LENGTH", 100))
    return 100


def _get_default_max_description_length() -> int:
    if has_app_context():
        return int(current_app.config.get("SHARE_MESSAGE_MAX_DESCRIPTION_LENGTH", 160))
    return 160


def _get_default_max_body_length() -> int:
    if has_app_context():
        return int(current_app.config.get("SHARE_MESSAGE_MAX_BODY_LENGTH", 500))
    return 500


def build_rule_based_share_message(
    article: Mapping[str, Any],
    *,
    prefix: str | None = None,
    max_title_length: int | None = None,
    max_description_length: int | None = None,
    max_body_length: int | None = None,
) -> dict[str, Any]:
    """Build a deterministic share message dictionary from an article record.

    Includes:
    - Configurable prefix
    - Article title (bounded by `max_title_length`)
    - Short description when available (bounded by `max_description_length`)
    - Original article URL (`canonical_url` / `target_url` / `url`)
    """
    if not isinstance(article, Mapping):
        raise ValidationError("Article must be a mapping/dictionary.")

    assert_no_forbidden_secrets(article)

    article_id = _collapse_whitespace(
        article.get("id") or article.get("article_id") or ""
    )
    if not article_id:
        raise ValidationError("Article 'id' (or 'article_id') is required.")

    raw_title = _collapse_whitespace(article.get("title") or "")
    if not raw_title:
        raise ValidationError("Article 'title' is required.")

    raw_url = (
        article.get("canonical_url")
        or article.get("target_url")
        or article.get("url")
        or article.get("link")
        or ""
    )
    target_url = normalize_url(str(raw_url), field_name="canonical_url")

    raw_description = _collapse_whitespace(
        article.get("summary")
        if article.get("summary") is not None
        else article.get("description") or ""
    )

    resolved_prefix = (
        _collapse_whitespace(prefix)
        if prefix is not None
        else _get_default_prefix()
    )
    resolved_max_title = (
        max_title_length
        if max_title_length is not None
        else _get_default_max_title_length()
    )
    resolved_max_desc = (
        max_description_length
        if max_description_length is not None
        else _get_default_max_description_length()
    )
    resolved_max_body = (
        max_body_length
        if max_body_length is not None
        else _get_default_max_body_length()
    )

    if resolved_max_title < 4:
        raise ValidationError("'max_title_length' must be at least 4 characters.")
    if resolved_max_desc < 4:
        raise ValidationError("'max_description_length' must be at least 4 characters.")
    if resolved_max_body < len(target_url) + 6:
        raise ValidationError(
            "'max_body_length' is too small to accommodate the original article URL."
        )

    bounded_title = truncate_text(raw_title, resolved_max_title)
    header_line = (
        f"{resolved_prefix} {bounded_title}".strip()
        if resolved_prefix
        else bounded_title
    )

    short_description = (
        truncate_text(raw_description, resolved_max_desc)
        if raw_description
        else ""
    )

    # Ensure total assembled body respects `resolved_max_body` while keeping `target_url` intact
    if short_description:
        candidate_body = f"{header_line}\n{short_description}\n{target_url}"
        if len(candidate_body) > resolved_max_body:
            available_for_desc = (
                resolved_max_body - len(header_line) - len(target_url) - 2
            )
            if available_for_desc >= 4:
                short_description = truncate_text(raw_description, available_for_desc)
                candidate_body = f"{header_line}\n{short_description}\n{target_url}"
            else:
                short_description = ""
                candidate_body = f"{header_line}\n{target_url}"
    else:
        candidate_body = f"{header_line}\n{target_url}"

    if len(candidate_body) > resolved_max_body:
        available_for_header = resolved_max_body - len(target_url) - 1
        if available_for_header < 4:
            raise ValidationError(
                "'max_body_length' is too small to fit the message header and URL."
            )
        header_line = truncate_text(header_line, available_for_header)
        if resolved_prefix and header_line.startswith(resolved_prefix):
            title_part = header_line[len(resolved_prefix) :].strip()
            if title_part:
                bounded_title = title_part
        else:
            bounded_title = header_line
        candidate_body = f"{header_line}\n{target_url}"

    return {
        "article_id": article_id,
        "title": bounded_title,
        "body": candidate_body,
        "target_url": target_url,
        "status": "pending",
    }


class RuleBasedShareMessageGenerator:
    """Service that generates and persists deduplicated `pending` share messages for articles."""

    def __init__(
        self,
        *,
        share_repo: ShareMessageRepository | None = None,
        prefix: str | None = None,
        max_title_length: int | None = None,
        max_description_length: int | None = None,
        max_body_length: int | None = None,
    ) -> None:
        self.share_repo = share_repo or ShareMessageRepository()
        self.prefix = prefix
        self.max_title_length = max_title_length
        self.max_description_length = max_description_length
        self.max_body_length = max_body_length

    def generate_for_article_with_status(
        self, article: Mapping[str, Any]
    ) -> tuple[RecordDict, bool]:
        """Generate and store a `pending` share message for `article`, avoiding duplicates."""
        payload = build_rule_based_share_message(
            article,
            prefix=self.prefix,
            max_title_length=self.max_title_length,
            max_description_length=self.max_description_length,
            max_body_length=self.max_body_length,
        )
        return self.share_repo.create_or_get_with_status(payload)

    def generate_for_article(self, article: Mapping[str, Any]) -> RecordDict:
        """Generate and store a `pending` share message for `article` (idempotent)."""
        record, _ = self.generate_for_article_with_status(article)
        return record


def edit_pending_share_message(
    message_id: str,
    payload: Mapping[str, Any],
    *,
    share_repo: ShareMessageRepository | None = None,
    max_title_length: int | None = None,
    max_body_length: int | None = None,
) -> dict[str, Any] | None:
    """Edit a `pending` share message's fields (`title`, `body`, `target_url`, `status`)."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Request body must be a JSON object.")

    repository = share_repo or ShareMessageRepository()
    resolved_max_title = (
        max_title_length
        if max_title_length is not None
        else _get_default_max_title_length()
    )
    resolved_max_body = (
        max_body_length
        if max_body_length is not None
        else _get_default_max_body_length()
    )

    updated = repository.update_pending_message(
        message_id,
        payload,
        max_title_length=resolved_max_title,
        max_body_length=resolved_max_body,
    )
    if not updated:
        return None
    return ShareMessageRepository.to_api_dict(updated)
