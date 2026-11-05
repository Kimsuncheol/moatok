"""Automated tests for Firestore repositories:
- `sources` (`SourceRepository`)
- `articles` (`ArticleRepository`)
- `share_messages` (`ShareMessageRepository`)
- `users/{userId}/devices` (`UserDeviceRepository`)
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest

from app.models import ValidationError
from app.repositories import (
    ArticleRepository,
    ShareMessageRepository,
    SourceRepository,
    UserDeviceRepository,
)


def _assert_is_utc_datetime(dt: datetime | None) -> None:
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(dt) == timedelta(0)


def test_source_repository_crud_and_utc_timestamps(fake_db):
    repo = SourceRepository(db=fake_db)
    kst = timezone(timedelta(hours=9))
    created_kst = datetime(2026, 11, 5, 22, 0, 0, tzinfo=kst)

    # 1. Create source with non-UTC timestamp -> stored in UTC
    source, created = repo.create_or_get_with_status(
        name="Tech News RSS",
        url="HTTPS://Example.com/rss/feed.xml#section",
        source_type="RSS",
        enabled=True,
        last_checked_at=None,
        created_at=created_kst,
    )
    assert created is True
    assert source["id"].startswith("src_")
    assert source["name"] == "Tech News RSS"
    assert source["url"] == "https://example.com/rss/feed.xml"
    assert source["source_type"] == "rss"
    assert source["enabled"] is True
    assert source["last_checked_at"] is None
    assert source["last_checked_time"] is None
    _assert_is_utc_datetime(source["created_at"])
    assert source["created_at"] == datetime(2026, 11, 5, 13, 0, 0, tzinfo=timezone.utc)
    assert source["creation_time"] == source["created_at"]

    # 2. Repeated creation of the same source URL returns the existing source without duplicating
    duplicate, created_again = repo.create_or_get_with_status(
        name="Tech News RSS Duplicate",
        url="https://example.com/rss/feed.xml",
        source_type="rss",
    )
    assert created_again is False
    assert duplicate["id"] == source["id"]
    assert duplicate["name"] == "Tech News RSS"
    assert len(repo.list_sources()) == 1

    # 3. Update last_checked_at with KST timestamp -> converted to UTC
    checked_kst = datetime(2026, 11, 5, 22, 30, 0, tzinfo=kst)
    updated = repo.update_last_checked(source["id"], checked_at=checked_kst)
    assert updated is not None
    _assert_is_utc_datetime(updated["last_checked_at"])
    assert updated["last_checked_at"] == datetime(
        2026, 11, 5, 13, 30, 0, tzinfo=timezone.utc
    )

    # 4. Disable source and filter by enabled_only
    disabled = repo.set_enabled(source["id"], False)
    assert disabled is not None
    assert disabled["enabled"] is False
    assert repo.list_sources(enabled_only=True) == []
    assert len(repo.list_sources(enabled_only=False)) == 1


def test_article_repository_deduplicates_repeated_and_concurrent_jobs(fake_db):
    repo = ArticleRepository(db=fake_db)
    kst = timezone(timedelta(hours=9))
    pub_time = datetime(2026, 11, 5, 9, 0, 0, tzinfo=kst)
    first_collected = datetime(2026, 11, 5, 10, 0, 0, tzinfo=kst)

    # 1. Create article
    article, created = repo.create_or_get_with_status(
        source_id="src_123",
        source_url="https://example.com/rss",
        canonical_url="https://example.com/articles/python-312/#comments",
        title="Python 3.12 Performance",
        summary="Interpreter improvements and typing updates.",
        published_at=pub_time,
        collected_at=first_collected,
    )
    assert created is True
    assert article["id"].startswith("art_")
    assert article["source_id"] == "src_123"
    assert article["source_url"] == "https://example.com/rss"
    assert article["canonical_url"] == "https://example.com/articles/python-312"
    assert article["title"] == "Python 3.12 Performance"
    assert article["summary"] == "Interpreter improvements and typing updates."
    _assert_is_utc_datetime(article["published_at"])
    _assert_is_utc_datetime(article["collected_at"])
    assert article["publication_time"] == article["published_at"]
    assert article["collection_time"] == article["collected_at"]

    # 2. Repeated job runs later with same canonical URL -> does not duplicate or overwrite collected_at
    later_collected = datetime(2026, 11, 5, 14, 0, 0, tzinfo=timezone.utc)
    repeated, created_second = repo.create_or_get_with_status(
        source_id="src_123",
        source_url="https://example.com/rss",
        canonical_url="HTTPS://Example.com/articles/python-312/",
        title="Python 3.12 Performance (Re-scraped)",
        summary="Updated summary",
        published_at=pub_time,
        collected_at=later_collected,
    )
    assert created_second is False
    assert repeated["id"] == article["id"]
    assert repeated["collected_at"] == article["collected_at"]
    assert len(repo.list_articles()) == 1

    # 3. Concurrent workers attempting to insert the same new article simultaneously
    def _worker_insert(worker_idx: int):
        return repo.create_or_get_with_status(
            source_id="src_123",
            source_url="https://example.com/rss",
            canonical_url="https://example.com/articles/concurrent-test",
            title=f"Concurrent Article from Worker {worker_idx}",
            summary="Concurrent summary",
            published_at="2026-11-05T08:00:00Z",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_worker_insert, range(8)))

    created_flags = [was_created for _, was_created in results]
    assert created_flags.count(True) == 1
    assert created_flags.count(False) == 7
    distinct_ids = {rec["id"] for rec, _ in results}
    assert len(distinct_ids) == 1
    assert len(repo.list_articles()) == 2


def test_share_message_repository_deduplicates_and_updates_status_in_utc(fake_db):
    repo = ShareMessageRepository(db=fake_db)
    kst = timezone(timedelta(hours=9))
    initial_time = datetime(2026, 11, 5, 18, 0, 0, tzinfo=kst)

    # 1. Create share message for an article
    msg, created = repo.create_or_get_with_status(
        article_id="art_abc123",
        title="오늘의 개발 브리핑",
        body="📌 Python 3.12 주요 변경사항 요약",
        target_url="https://example.com/articles/python-312",
        status="ready_to_share",
        created_at=initial_time,
        updated_at=initial_time,
    )
    assert created is True
    assert msg["id"].startswith("msg_")
    assert msg["article_id"] == "art_abc123"
    assert msg["title"] == "오늘의 개발 브리핑"
    assert msg["body"] == "📌 Python 3.12 주요 변경사항 요약"
    assert msg["target_url"] == "https://example.com/articles/python-312"
    assert msg["status"] == "ready_to_share"
    _assert_is_utc_datetime(msg["created_at"])
    _assert_is_utc_datetime(msg["updated_at"])
    assert msg["creation_time"] == msg["created_at"]
    assert msg["update_time"] == msg["updated_at"]

    # 2. Concurrent / repeated jobs trying to create a share message for the same article_id
    def _concurrent_create(idx: int):
        return repo.create_or_get_with_status(
            article_id="art_abc123",
            title=f"Duplicate Title {idx}",
            body="Duplicate body",
            target_url="https://example.com/articles/python-312",
            status="ready_to_share",
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(_concurrent_create, range(6)))

    assert all(was_created is False for _, was_created in outcomes)
    assert len(repo.list_messages()) == 1
    assert repo.get_by_article_id("art_abc123")["title"] == "오늘의 개발 브리핑"

    # 3. Update status in transaction with UTC timestamp
    updated = repo.update_status(
        msg["id"],
        status="shared_by_user",
        updated_at="2026-11-05T10:30:00+00:00",
    )
    assert updated is not None
    assert updated["status"] == "shared_by_user"
    _assert_is_utc_datetime(updated["updated_at"])
    assert updated["updated_at"] == datetime(
        2026, 11, 5, 10, 30, 0, tzinfo=timezone.utc
    )


def test_user_device_repository_subcollection_isolation_and_upsert(fake_db):
    repo = UserDeviceRepository(db=fake_db)

    # 1. Register device under users/user-1/devices
    dev1 = repo.upsert_device(
        user_id="user-1",
        fcm_token="fcm-token-user1-ios",
        platform="Flutter_iOS",
    )
    assert dev1["user_id"] == "user-1"
    assert dev1["device_id"].startswith("dev_")
    assert dev1["fcm_token"] == "fcm-token-user1-ios"
    assert dev1["platform"] == "flutter_ios"
    assert dev1["enabled"] is True
    _assert_is_utc_datetime(dev1["created_at"])
    _assert_is_utc_datetime(dev1["updated_at"])
    _assert_is_utc_datetime(dev1["last_seen_at"])

    # Verify subcollection path in Firestore is `users/user-1/devices`
    assert "users/user-1/devices" in fake_db.collections
    assert dev1["device_id"] in fake_db.collections["users/user-1/devices"]

    # 2. Repeated upsert with same token updates existing device without duplicating
    original_created_at = dev1["created_at"]
    later_time = original_created_at + timedelta(minutes=15)
    dev1_updated = repo.upsert_device(
        user_id="user-1",
        fcm_token="fcm-token-user1-ios",
        platform="flutter_ios",
        updated_at=later_time,
    )
    assert dev1_updated["device_id"] == dev1["device_id"]
    assert dev1_updated["created_at"] == original_created_at
    assert dev1_updated["updated_at"] == later_time
    assert len(repo.list_devices("user-1")) == 1

    # 3. Register device for user-2 and verify per-user subcollection isolation
    dev2 = repo.upsert_device(
        user_id="user-2",
        fcm_token="fcm-token-user2-android",
        platform="flutter_android",
    )
    assert len(repo.list_devices("user-1")) == 1
    assert len(repo.list_devices("user-2")) == 1
    assert repo.get_device("user-1", dev2["device_id"]) is None

    # 4. Deactivate and delete device
    deactivated = repo.deactivate_device("user-1", dev1["device_id"])
    assert deactivated is not None
    assert deactivated["enabled"] is False
    assert repo.list_devices("user-1", enabled_only=True) == []

    assert repo.delete_device("user-1", dev1["device_id"]) is True
    assert repo.get_device("user-1", dev1["device_id"]) is None


@pytest.mark.parametrize(
    "forbidden_payload",
    [
        {"kakao_access_token": "kakao-secret-access-token"},
        {"kakao_refresh_token": "kakao-secret-refresh-token"},
        {"access_token": "oauth-access-token"},
        {"service_account_key": {"type": "service_account", "private_key": "secret"}},
        {"private_key": "-----BEGIN PRIVATE KEY-----\nMIIEv..."},
        {"type": "service_account", "client_email": "bot@project.iam.gserviceaccount.com"},
    ],
)
def test_repositories_reject_kakao_tokens_and_service_account_keys(
    fake_db, forbidden_payload
):
    """Ensure Kakao access tokens and service account keys can never be stored in Firestore."""
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)
    share_repo = ShareMessageRepository(db=fake_db)
    device_repo = UserDeviceRepository(db=fake_db)

    with pytest.raises(ValidationError, match="prohibited"):
        source_repo.create(
            {
                "name": "Test Source",
                "url": "https://example.com/rss",
                "source_type": "rss",
                **forbidden_payload,
            }
        )

    with pytest.raises(ValidationError, match="prohibited"):
        article_repo.create(
            {
                "source_id": "src_1",
                "source_url": "https://example.com/rss",
                "canonical_url": "https://example.com/post/1",
                "title": "Post 1",
                "summary": "Summary",
                **forbidden_payload,
            }
        )

    with pytest.raises(ValidationError, match="prohibited"):
        share_repo.create(
            {
                "article_id": "art_1",
                "title": "Share Title",
                "body": "Share Body",
                "target_url": "https://example.com/post/1",
                **forbidden_payload,
            }
        )

    with pytest.raises(ValidationError, match="prohibited"):
        device_repo.upsert_device(
            "user-1",
            {
                "fcm_token": "fcm-token-123",
                "platform": "flutter",
                **forbidden_payload,
            },
        )

    assert fake_db.collections == {}
