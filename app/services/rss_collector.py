"""RSS collection service for fetching enabled RSS sources, parsing feeds, and storing deduplicated articles."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from app.models import ValidationError
from app.repositories.articles_repo import ArticleRepository
from app.repositories.firestore_utils import (
    ensure_utc_datetime,
    normalize_url,
    utc_now,
)
from app.repositories.share_messages_repo import ShareMessageRepository
from app.repositories.sources_repo import SourceRepository
from app.services.share_message_generator import RuleBasedShareMessageGenerator
from app.services.url_validator import fetch_and_validate_source_url

logger = logging.getLogger(__name__)

TRACKING_QUERY_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }
)

_URL_CREDENTIALS_RE = re.compile(r"(https?://)([^/\s:@]+:[^/\s@]+@)", re.IGNORECASE)
_SENSITIVE_PARAM_RE = re.compile(
    r"([?&](?:api[_-]?key|token|access[_-]?token|refresh[_-]?token|secret|password|auth|sig| signature|key)=)([^&\s]+)",
    re.IGNORECASE,
)
_BEARER_TOKEN_RE = re.compile(
    r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class ParsedRssItem:
    """Normalized representation of a single parsed RSS/Atom entry."""

    title: str
    link: str
    canonical_url: str
    stable_id: str
    summary: str = ""
    published_at: datetime | None = None


def sanitize_log_detail(detail: Any) -> str:
    """Redact credentials, tokens, and secret query parameters from log messages."""
    text = str(detail or "")
    text = _URL_CREDENTIALS_RE.sub(r"\1[REDACTED]@", text)
    text = _SENSITIVE_PARAM_RE.sub(r"\1[REDACTED]", text)
    text = _BEARER_TOKEN_RE.sub(r"\1 [REDACTED]", text)
    return text


def canonicalize_article_url(url: str, *, base_url: str | None = None) -> str:
    """Resolve relative links, strip tracking query parameters, and normalize the URL."""
    raw = str(url or "").strip()
    if not raw:
        raise ValidationError("Article link URL is empty.")
    if base_url:
        raw = urljoin(base_url, raw)

    normalized = normalize_url(raw, field_name="canonical_url")
    parts = urlsplit(normalized)
    if parts.query:
        filtered_params = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in TRACKING_QUERY_PARAMS
        ]
        cleaned_query = urlencode(filtered_params, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, cleaned_query, ""))
    return normalized


def parse_publication_date(raw_value: str | None) -> datetime | None:
    """Parse RFC 2822 (`pubDate`) or ISO-8601 (`published`/`updated`) dates into UTC."""
    if raw_value is None:
        return None
    cleaned = str(raw_value).strip()
    if not cleaned:
        return None

    # 1. Try RFC 2822 format standard in RSS 2.0 (e.g. "Thu, 05 Nov 2026 13:00:00 GMT")
    try:
        dt = parsedate_to_datetime(cleaned)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass

    # 2. Try ISO-8601 format standard in Atom / Dublin Core (`dc:date`)
    try:
        return ensure_utc_datetime(cleaned, field_name="published_at", allow_none=True)
    except ValidationError:
        return None


def _clean_summary_text(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    unescaped = html.unescape(str(raw_text))
    stripped = _HTML_TAG_RE.sub(" ", unescaped)
    return " ".join(stripped.split()).strip()


def _local_tag(tag: str) -> str:
    """Strip XML namespace URI `{http://...}local` -> `local`."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1].lower()
    return tag.lower()


def _extract_item_element(elem: ET.Element, *, source_url: str) -> ParsedRssItem:
    title_val = ""
    link_val = ""
    canonical_link_val = ""
    guid_val = ""
    guid_is_permalink = True
    description_val = ""
    content_val = ""
    pub_date_raw = ""

    for child in elem:
        lname = _local_tag(child.tag)
        text = (child.text or "").strip()

        if lname == "title" and not title_val and text:
            title_val = html.unescape(text).strip()
        elif lname == "link":
            rel = (child.attrib.get("rel") or "").strip().lower()
            href = (child.attrib.get("href") or "").strip()
            if href:
                if rel == "canonical" and not canonical_link_val:
                    canonical_link_val = href
                elif rel in {"", "alternate"} and not link_val:
                    link_val = href
                elif not link_val:
                    link_val = href
            elif text:
                if rel == "canonical" and not canonical_link_val:
                    canonical_link_val = text
                elif not link_val:
                    link_val = text
        elif lname in {"guid", "id"} and not guid_val and text:
            guid_val = text
            is_permalink_attr = (
                child.attrib.get("isPermaLink")
                or child.attrib.get("ispermalink")
                or "true"
            ).strip().lower()
            guid_is_permalink = is_permalink_attr != "false"
        elif lname in {"description", "summary"} and not description_val and text:
            description_val = text
        elif lname in {"encoded", "content"} and not content_val and text:
            content_val = text
        elif lname in {"pubdate", "published", "date", "updated"} and not pub_date_raw and text:
            pub_date_raw = text

    if not title_val:
        raise ValidationError("Feed item is missing a non-empty <title>.")

    # Resolve primary link and canonical URL
    primary_link_candidate = canonical_link_val or link_val
    if not primary_link_candidate and guid_val and guid_is_permalink:
        primary_link_candidate = guid_val

    if not primary_link_candidate:
        raise ValidationError("Feed item is missing a valid <link> or canonical URL.")

    resolved_link = canonicalize_article_url(
        link_val or primary_link_candidate, base_url=source_url
    )

    if canonical_link_val:
        canonical_url = canonicalize_article_url(
            canonical_link_val, base_url=source_url
        )
    elif guid_val and guid_is_permalink:
        try:
            canonical_url = canonicalize_article_url(guid_val, base_url=source_url)
        except ValidationError:
            canonical_url = resolved_link
    else:
        canonical_url = resolved_link

    # Prefer source-provided stable ID (`guid` / `id`), normalized if it's a URL,
    # or fall back to `canonical_url`.
    if guid_val:
        try:
            stable_id = canonicalize_article_url(guid_val)
        except ValidationError:
            stable_id = guid_val.strip()
    else:
        stable_id = canonical_url

    summary_text = _clean_summary_text(description_val or content_val)
    published_at = parse_publication_date(pub_date_raw)

    return ParsedRssItem(
        title=title_val,
        link=resolved_link,
        canonical_url=canonical_url,
        stable_id=stable_id,
        summary=summary_text,
        published_at=published_at,
    )


def parse_rss_feed(
    xml_payload: bytes | str,
    *,
    source_id: str,
    source_url: str,
) -> tuple[list[ParsedRssItem], int]:
    """Parse an RSS 2.0, RDF, or Atom XML payload.

    Returns:
        Tuple of (valid_parsed_items, failed_item_count).
    Raises:
        ValidationError: If the overall XML document is malformed or not a feed.
    """
    if isinstance(xml_payload, bytes):
        raw_text = xml_payload.decode("utf-8", errors="replace").strip()
    else:
        raw_text = str(xml_payload or "").strip()

    if not raw_text:
        raise ValidationError("Empty RSS feed response.")

    if "<!ENTITY" in raw_text.upper():
        raise ValidationError("XML entity declarations are not permitted in RSS feeds.")

    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError as exc:
        raise ValidationError(f"Malformed RSS/Atom XML: {exc}") from exc

    root_name = _local_tag(root.tag)
    item_elements: list[ET.Element] = []

    if root_name == "rss":
        for child in root:
            if _local_tag(child.tag) == "channel":
                for sub in child:
                    if _local_tag(sub.tag) == "item":
                        item_elements.append(sub)
    elif root_name == "feed":
        for child in root:
            if _local_tag(child.tag) == "entry":
                item_elements.append(child)
    elif root_name == "rdf":
        for child in root:
            if _local_tag(child.tag) == "item":
                item_elements.append(child)
    else:
        raise ValidationError(
            f"Unsupported XML root element '<{root_name}>'; expected <rss> or <feed>."
        )

    parsed_items: list[ParsedRssItem] = []
    failed_items = 0

    for idx, elem in enumerate(item_elements):
        try:
            item = _extract_item_element(elem, source_url=source_url)
            parsed_items.append(item)
        except Exception as exc:
            failed_items += 1
            logger.warning(
                "Skipping invalid feed item (source_id=%s, item_index=%d): %s",
                source_id,
                idx,
                sanitize_log_detail(exc),
            )

    return parsed_items, failed_items


class RssCollectionService:
    """Service that collects articles from enabled RSS sources and persists new articles in Firestore."""

    def __init__(
        self,
        *,
        source_repo: SourceRepository | None = None,
        article_repo: ArticleRepository | None = None,
        share_repo: ShareMessageRepository | None = None,
        share_generator: RuleBasedShareMessageGenerator | None = None,
        http_open: Callable[..., Any] | None = None,
        allowed_domains: Iterable[str] | None = None,
        timeout_seconds: float | None = None,
        max_bytes: int | None = None,
        max_redirects: int | None = None,
    ) -> None:
        self.source_repo = source_repo or SourceRepository()
        self.article_repo = article_repo or ArticleRepository()
        self.share_repo = share_repo or ShareMessageRepository(db=self.article_repo.db)
        self.share_generator = share_generator or RuleBasedShareMessageGenerator(
            share_repo=self.share_repo
        )
        self.http_open = http_open
        self.allowed_domains = allowed_domains
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    def collect_all(self) -> dict[str, Any]:
        """Fetch all enabled RSS sources, store deduplicated articles, and return a job summary."""
        enabled_sources = [
            src
            for src in self.source_repo.list_sources(enabled_only=True)
            if str(src.get("source_type") or "").strip().lower() == "rss"
        ]

        total_processed = 0
        total_new = 0
        total_duplicate = 0
        total_failed = 0
        total_share_messages_created = 0
        sources_succeeded = 0
        sources_failed = 0
        source_summaries: list[dict[str, Any]] = []

        for source in enabled_sources:
            source_id = str(source.get("id") or "")
            source_url = str(source.get("url") or "")
            src_processed = 0
            src_new = 0
            src_duplicate = 0
            src_failed = 0
            src_share_messages = 0
            src_error: str | None = None

            try:
                probe = fetch_and_validate_source_url(
                    source_url,
                    allowed_domains=self.allowed_domains,
                    timeout_seconds=self.timeout_seconds,
                    max_bytes=self.max_bytes,
                    max_redirects=self.max_redirects,
                    http_open=self.http_open,
                )
                items, item_parse_failures = parse_rss_feed(
                    probe.content,
                    source_id=source_id,
                    source_url=probe.final_url,
                )
                src_failed += item_parse_failures
                src_processed += item_parse_failures

                for item in items:
                    src_processed += 1
                    try:
                        article_record, created = (
                            self.article_repo.create_or_get_with_status(
                                source_id=source_id,
                                source_url=probe.final_url,
                                canonical_url=item.canonical_url,
                                stable_id=item.stable_id,
                                title=item.title,
                                summary=item.summary,
                                published_at=item.published_at,
                                collected_at=utc_now(),
                            )
                        )
                        if created:
                            src_new += 1
                            _, msg_created = (
                                self.share_generator.generate_for_article_with_status(
                                    article_record
                                )
                            )
                            if msg_created:
                                src_share_messages += 1
                        else:
                            src_duplicate += 1
                    except Exception as item_exc:
                        src_failed += 1
                        logger.error(
                            "Failed to store article for source_id=%s: %s",
                            source_id,
                            sanitize_log_detail(item_exc),
                        )

                try:
                    self.source_repo.update_last_checked(source_id, checked_at=utc_now())
                except Exception as update_exc:
                    logger.warning(
                        "Failed to update last_checked_at for source_id=%s: %s",
                        source_id,
                        sanitize_log_detail(update_exc),
                    )

                sources_succeeded += 1

            except Exception as exc:
                sources_failed += 1
                src_failed += 1
                src_error = sanitize_log_detail(exc)
                logger.error(
                    "RSS collection failed for source_id=%s: %s",
                    source_id,
                    src_error,
                )

            total_processed += src_processed
            total_new += src_new
            total_duplicate += src_duplicate
            total_failed += src_failed
            total_share_messages_created += src_share_messages

            source_summaries.append(
                {
                    "source_id": source_id,
                    "status": "failed" if src_error else "ok",
                    "processed": src_processed,
                    "new": src_new,
                    "duplicate": src_duplicate,
                    "failed": src_failed,
                    "share_messages_created": src_share_messages,
                    "error": src_error,
                }
            )

        return {
            "sources_checked": len(enabled_sources),
            "sources_succeeded": sources_succeeded,
            "sources_failed": sources_failed,
            "processed": total_processed,
            "new": total_new,
            "duplicate": total_duplicate,
            "failed": total_failed,
            "share_messages_created": total_share_messages_created,
            "processed_count": total_processed,
            "new_count": total_new,
            "duplicate_count": total_duplicate,
            "failed_count": total_failed,
            "processed_items": total_processed,
            "new_items": total_new,
            "duplicate_items": total_duplicate,
            "failed_items": total_failed,
            "sources": source_summaries,
        }


def collect_rss_articles(
    *,
    source_repo: SourceRepository | None = None,
    article_repo: ArticleRepository | None = None,
    share_repo: ShareMessageRepository | None = None,
    share_generator: RuleBasedShareMessageGenerator | None = None,
    http_open: Callable[..., Any] | None = None,
    allowed_domains: Iterable[str] | None = None,
    timeout_seconds: float | None = None,
    max_bytes: int | None = None,
    max_redirects: int | None = None,
) -> dict[str, Any]:
    """Convenience entrypoint to run an RSS collection job and return the summary."""
    service = RssCollectionService(
        source_repo=source_repo,
        article_repo=article_repo,
        share_repo=share_repo,
        share_generator=share_generator,
        http_open=http_open,
        allowed_domains=allowed_domains,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        max_redirects=max_redirects,
    )
    return service.collect_all()
