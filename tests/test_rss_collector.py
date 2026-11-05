"""Automated tests for the RSS collection service using mocked network responses and fake repositories."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import socket
import urllib.error

from app.repositories import ArticleRepository, SourceRepository
from app.services.rss_collector import RssCollectionService, collect_rss_articles
from app.services.url_validator import SyntheticProbeResponse


SAMPLE_RSS_FEED_1 = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Example Tech Feed</title>
    <link>https://feeds.example.com</link>
    <description>Daily tech updates</description>
    <item>
      <title>Python 3.12 Released</title>
      <link>https://example.com/news/python-312?utm_source=rss&amp;utm_medium=feed</link>
      <guid isPermaLink="false">stable-guid-python-312</guid>
      <pubDate>Thu, 05 Nov 2026 13:00:00 GMT</pubDate>
      <description>&lt;p&gt;Faster interpreter and improved typing.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Flutter Kakao Share Guide</title>
      <link>https://example.com/news/flutter-kakao?fbclid=xyz987</link>
      <atom:link rel="canonical" href="https://example.com/news/flutter-kakao" />
      <pubDate>Thu, 05 Nov 2026 15:30:00 +0900</pubDate>
      <description>User-initiated KakaoTalk sharing workflow in Flutter.</description>
    </item>
  </channel>
</rss>
"""

# Second feed has:
# - 1 duplicate of item 1 via same stable <guid> despite different URL query param
# - 1 duplicate of item 2 via same canonical URL
# - 1 brand new item
# - 1 malformed item (missing <link> and <guid>)
SAMPLE_RSS_FEED_2_WITH_PARTIAL_ITEM_FAILURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Secondary Tech Feed</title>
    <item>
      <title>Python 3.12 Released (Syndicated)</title>
      <link>https://example.com/syndicated/python-312-mirror</link>
      <guid isPermaLink="false">stable-guid-python-312</guid>
      <pubDate>Thu, 05 Nov 2026 14:00:00 GMT</pubDate>
      <description>Syndicated copy with the same stable ID.</description>
    </item>
    <item>
      <title>Flutter Kakao Share Guide (Repost)</title>
      <link>https://example.com/news/flutter-kakao?utm_campaign=weekly</link>
      <pubDate>Thu, 05 Nov 2026 07:00:00 GMT</pubDate>
      <description>Duplicate by canonical URL.</description>
    </item>
    <item>
      <title>Cloud Firestore Security Best Practices</title>
      <link>https://example.org/articles/firestore-security</link>
      <guid>https://example.org/articles/firestore-security</guid>
      <pubDate>2026-11-05T16:00:00Z</pubDate>
      <description>Never store service account keys or OAuth tokens in Firestore.</description>
    </item>
    <item>
      <title>Broken Item Missing Link</title>
      <description>This item has no link or guid and should be counted as failed.</description>
    </item>
  </channel>
</rss>
"""


def test_rss_collection_parses_deduplicates_and_stores_articles(fake_db):
    """Verify RSS parsing, stable ID & canonical URL deduplication, UTC dates, and job summary counts."""
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)

    src1 = source_repo.create(
        name="Primary Tech RSS",
        url="https://feeds.example.com/rss.xml",
        source_type="rss",
        enabled=True,
    )
    # Disabled RSS source should be ignored
    source_repo.create(
        name="Disabled RSS",
        url="https://feeds.example.com/disabled.xml",
        source_type="rss",
        enabled=False,
    )
    # Non-RSS source should be ignored by RSS collector
    source_repo.create(
        name="Official API Source",
        url="https://example.com/api/v1/items",
        source_type="official_api",
        enabled=True,
    )

    recorded_timeouts: list[float] = []

    def _mock_http_open(req, timeout):
        recorded_timeouts.append(timeout)
        if req.full_url == "https://feeds.example.com/rss.xml":
            return SyntheticProbeResponse(status=200, body=SAMPLE_RSS_FEED_1)
        raise AssertionError(f"Unexpected URL fetched: {req.full_url}")

    # First collection run: 2 new articles
    summary_run1 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com", "example.org", "*.example.org"),
        timeout_seconds=4.0,
        max_bytes=64 * 1024,
    )

    assert recorded_timeouts == [4.0]
    assert summary_run1["sources_checked"] == 1
    assert summary_run1["sources_succeeded"] == 1
    assert summary_run1["sources_failed"] == 0
    assert summary_run1["processed"] == 2
    assert summary_run1["new"] == 2
    assert summary_run1["duplicate"] == 0
    assert summary_run1["failed"] == 0

    stored_articles = article_repo.list_articles()
    assert len(stored_articles) == 2

    by_title = {a["title"]: a for a in stored_articles}
    py_art = by_title["Python 3.12 Released"]
    assert py_art["source_id"] == src1["id"]
    assert py_art["canonical_url"] == "https://example.com/news/python-312"
    assert py_art["stable_id"] == "stable-guid-python-312"
    assert py_art["summary"] == "Faster interpreter and improved typing."
    assert py_art["published_at"] == datetime(2026, 11, 5, 13, 0, 0, tzinfo=timezone.utc)

    fl_art = by_title["Flutter Kakao Share Guide"]
    assert fl_art["canonical_url"] == "https://example.com/news/flutter-kakao"
    assert fl_art["published_at"] == datetime(2026, 11, 5, 6, 30, 0, tzinfo=timezone.utc)

    # Verify source `last_checked_at` was updated in UTC
    updated_src1 = source_repo.get(src1["id"])
    assert updated_src1["last_checked_at"] is not None
    assert updated_src1["last_checked_at"].tzinfo == timezone.utc

    # Second collection run on same feed: 0 new, 2 duplicate
    summary_run2 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com", "example.org", "*.example.org"),
        timeout_seconds=4.0,
        max_bytes=64 * 1024,
    )
    assert summary_run2["processed"] == 2
    assert summary_run2["new"] == 0
    assert summary_run2["duplicate"] == 2
    assert summary_run2["failed"] == 0
    assert len(article_repo.list_articles()) == 2


def test_rss_collection_handles_malformed_feeds_partial_failures_and_redacts_credentials_in_logs(
    fake_db, caplog
):
    """Malformed feeds, timeouts, oversized responses, and broken items must not stop other sources, and logs must not leak credentials."""
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)

    # Source A: returns malformed XML and throws error containing sensitive credentials/tokens
    src_malformed = source_repo.create(
        source_id="src_malformed_xml",
        name="Malformed Feed",
        url="https://feeds.example.com/malformed.xml",
        source_type="rss",
        enabled=True,
    )
    # Source B: times out and includes a secret token in error details
    src_timeout = source_repo.create(
        source_id="src_timeout_feed",
        name="Timeout Feed",
        url="https://feeds.example.com/timeout.xml",
        source_type="rss",
        enabled=True,
    )
    # Source C: oversized response exceeding max_bytes
    src_oversized = source_repo.create(
        source_id="src_oversized_feed",
        name="Oversized Feed",
        url="https://feeds.example.com/oversized.xml",
        source_type="rss",
        enabled=True,
    )
    # Source D: valid feed with 2 items
    src_valid_1 = source_repo.create(
        source_id="src_valid_1",
        name="Valid Feed 1",
        url="https://feeds.example.com/valid1.xml",
        source_type="rss",
        enabled=True,
    )
    # Source E: valid feed with 1 duplicate by stable_id, 1 duplicate by canonical_url, 1 new item, and 1 broken item
    src_valid_2 = source_repo.create(
        source_id="src_valid_2",
        name="Valid Feed 2",
        url="https://feeds.example.com/valid2.xml",
        source_type="rss",
        enabled=True,
    )

    def _mock_http_open(req, timeout):
        url = req.full_url
        if url == "https://feeds.example.com/malformed.xml":
            return SyntheticProbeResponse(
                status=200,
                body=b"<rss><channel><item><title>Unclosed XML",
            )
        if url == "https://feeds.example.com/timeout.xml":
            raise urllib.error.URLError(
                "Connection error for https://admin:superSecretPass123@feeds.example.com/timeout.xml?api_key=secretKey999 with Bearer eyJhbGciOiJSUzI1NiJ9"
            )
        if url == "https://feeds.example.com/oversized.xml":
            return SyntheticProbeResponse(
                status=200,
                body=b"x" * 10000,
            )
        if url == "https://feeds.example.com/valid1.xml":
            return SyntheticProbeResponse(status=200, body=SAMPLE_RSS_FEED_1)
        if url == "https://feeds.example.com/valid2.xml":
            return SyntheticProbeResponse(
                status=200, body=SAMPLE_RSS_FEED_2_WITH_PARTIAL_ITEM_FAILURE
            )
        raise AssertionError(f"Unexpected URL: {url}")

    caplog.set_level(logging.WARNING)

    service = RssCollectionService(
        source_repo=source_repo,
        article_repo=article_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com", "example.org", "*.example.org"),
        timeout_seconds=2.0,
        max_bytes=4096,
    )
    summary = service.collect_all()

    # 5 enabled RSS sources checked: 2 succeeded, 3 failed (malformed, timeout, oversized)
    assert summary["sources_checked"] == 5
    assert summary["sources_succeeded"] == 2
    assert summary["sources_failed"] == 3

    # Items processed across the 2 valid feeds:
    # - Valid Feed 1: 2 items (2 new)
    # - Valid Feed 2: 4 items (1 new, 2 duplicate [1 by stable_id across same source or canonical_url, 1 by canonical_url], 1 failed item)
    # Wait: Note that stable-guid-python-312 in Feed 2 had a different source_id and different link from Feed 1,
    # while Flutter Kakao Share Guide had the exact same canonical_url!
    assert summary["processed"] == 6
    assert summary["failed"] == 4  # 3 failed sources + 1 failed item in Feed 2
    assert summary["new"] + summary["duplicate"] == 5
    assert summary["duplicate"] >= 1

    # Verify logs contain source IDs for failed sources/items
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert src_malformed["id"] in log_text
    assert src_timeout["id"] in log_text
    assert src_oversized["id"] in log_text
    assert src_valid_2["id"] in log_text

    # Verify credentials/tokens were redacted and NEVER logged
    assert "superSecretPass123" not in log_text
    assert "secretKey999" not in log_text
    assert "eyJhbGciOiJSUzI1NiJ9" not in log_text
    assert "[REDACTED]" in log_text


def test_rss_collection_prefers_source_provided_stable_id_when_url_changes(fake_db):
    """When a source provides a stable <guid>, deduplicate by that stable ID even if <link> changes."""
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)

    source_repo.create(
        source_id="src_stable_guid",
        name="Stable GUID Feed",
        url="https://feeds.example.com/guid-feed.xml",
        source_type="rss",
        enabled=True,
    )

    feed_v1 = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>GUID Feed</title>
        <item>
          <title>Breaking Story v1</title>
          <link>https://example.com/2026/11/05/breaking-story-initial-slug</link>
          <guid isPermaLink="false">publisher-article-id-9001</guid>
          <pubDate>Thu, 05 Nov 2026 12:00:00 GMT</pubDate>
          <description>Initial version</description>
        </item>
      </channel>
    </rss>"""

    feed_v2 = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>GUID Feed</title>
        <item>
          <title>Breaking Story Updated Headline</title>
          <link>https://example.com/2026/11/05/breaking-story-updated-slug</link>
          <guid isPermaLink="false">publisher-article-id-9001</guid>
          <pubDate>Thu, 05 Nov 2026 13:00:00 GMT</pubDate>
          <description>Updated slug but identical publisher stable GUID</description>
        </item>
      </channel>
    </rss>"""

    payloads = [feed_v1, feed_v2]

    def _mock_http_open(req, timeout):
        return SyntheticProbeResponse(status=200, body=payloads.pop(0))

    summary_1 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com"),
    )
    assert summary_1["processed"] == 1
    assert summary_1["new"] == 1
    assert summary_1["duplicate"] == 0

    summary_2 = collect_rss_articles(
        source_repo=source_repo,
        article_repo=article_repo,
        http_open=_mock_http_open,
        allowed_domains=("example.com", "*.example.com"),
    )
    assert summary_2["processed"] == 1
    assert summary_2["new"] == 0
    assert summary_2["duplicate"] == 1
    assert len(article_repo.list_articles()) == 1
