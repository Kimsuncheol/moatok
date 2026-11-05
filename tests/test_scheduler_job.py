"""Tests for the protected Cloud Scheduler POST /internal/jobs/collect endpoint."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from typing import Any
from urllib.error import HTTPError

import pytest

from app.repositories import (
    ArticleRepository,
    ShareMessageRepository,
    SourceRepository,
    UserDeviceRepository,
)


class _MockHttpResponse:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.status = status
        self.headers = headers or {"Content-Type": "application/rss+xml; charset=utf-8"}
        self._offset = 0

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            chunk = self._body[self._offset :]
            self._offset = len(self._body)
            return chunk
        chunk = self._body[self._offset : self._offset + amt]
        self._offset += len(chunk)
        return chunk

    def close(self) -> None:
        pass

    def __enter__(self) -> _MockHttpResponse:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


SAMPLE_RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Moatok Scheduled Feed</title>
    <item>
      <guid>sched-guid-101</guid>
      <title>Scheduled Article One</title>
      <link>https://feeds.example.com/posts/101?utm_source=rss</link>
      <description>Summary of scheduled article one.</description>
      <pubDate>Wed, 05 Nov 2026 09:00:00 GMT</pubDate>
    </item>
    <item>
      <guid>sched-guid-102</guid>
      <title>Scheduled Article Two</title>
      <link>https://feeds.example.com/posts/102</link>
      <description>Summary of scheduled article two.</description>
      <pubDate>Wed, 05 Nov 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


@pytest.fixture()
def mock_scheduler_oidc(monkeypatch):
    """Mock Google OIDC token verification for Cloud Scheduler tests."""
    recorded_calls: list[dict[str, Any]] = []

    def _verify(token: str, audience: str | None = None) -> dict[str, Any]:
        recorded_calls.append({"token": token, "audience": audience})
        if token == "valid-scheduler-oidc-token":
            return {
                "iss": "https://accounts.google.com",
                "sub": "1234567890",
                "email": "moatok-scheduler@test-moatok-project.iam.gserviceaccount.com",
                "email_verified": True,
                "aud": audience,
            }
        if token == "wrong-sa-oidc-token":
            return {
                "iss": "https://accounts.google.com",
                "sub": "9999999999",
                "email": "other-caller@test-moatok-project.iam.gserviceaccount.com",
                "email_verified": True,
                "aud": audience,
            }
        if token == "unverified-email-oidc-token":
            return {
                "iss": "https://accounts.google.com",
                "sub": "1234567890",
                "email": "moatok-scheduler@test-moatok-project.iam.gserviceaccount.com",
                "email_verified": False,
                "aud": audience,
            }
        if token == "invalid-issuer-oidc-token":
            return {
                "iss": "https://evil.example.com",
                "sub": "1234567890",
                "email": "moatok-scheduler@test-moatok-project.iam.gserviceaccount.com",
                "email_verified": True,
                "aud": audience,
            }
        if token == "missing-email-oidc-token":
            return {
                "iss": "https://accounts.google.com",
                "sub": "1234567890",
                "email_verified": True,
                "aud": audience,
            }
        raise ValueError("Invalid or expired OIDC token")

    monkeypatch.setattr("app.auth.verify_scheduler_oidc_token", _verify)
    return recorded_calls


class TestSchedulerAuthenticationAndAuthorization:
    """Verify OIDC authentication, service account authorization, and fail-closed behavior."""

    def test_missing_authorization_header_returns_401(
        self, client, mock_scheduler_oidc
    ):
        resp = client.post("/internal/jobs/collect")
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["error"] == "unauthorized"
        assert body["code"] == "missing_token"

    def test_malformed_authorization_header_returns_401(
        self, client, mock_scheduler_oidc
    ):
        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["error"] == "unauthorized"
        assert body["code"] == "invalid_token"

    def test_invalid_or_expired_oidc_token_returns_401(
        self, client, mock_scheduler_oidc
    ):
        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer expired-or-forged-token"},
        )
        assert resp.status_code == 401
        body = resp.get_json()
        assert body["error"] == "unauthorized"
        assert body["code"] == "invalid_scheduler_token"

    def test_unverified_email_or_bad_issuer_or_missing_email_returns_401(
        self, client, mock_scheduler_oidc
    ):
        for bad_token in (
            "unverified-email-oidc-token",
            "invalid-issuer-oidc-token",
            "missing-email-oidc-token",
        ):
            resp = client.post(
                "/internal/jobs/collect",
                headers={"Authorization": f"Bearer {bad_token}"},
            )
            assert resp.status_code == 401
            body = resp.get_json()
            assert body["error"] == "unauthorized"
            assert body["code"] == "invalid_scheduler_token"

    def test_unexpected_service_account_returns_403(
        self, client, mock_scheduler_oidc
    ):
        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer wrong-sa-oidc-token"},
        )
        assert resp.status_code == 403
        body = resp.get_json()
        assert body["error"] == "forbidden"
        assert body["code"] == "unauthorized_service_account"

    def test_fails_closed_when_scheduler_service_account_not_configured(
        self, app, client, mock_scheduler_oidc
    ):
        app.config["SCHEDULER_SERVICE_ACCOUNT_EMAIL"] = None
        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
        )
        assert resp.status_code == 403
        body = resp.get_json()
        assert body["error"] == "forbidden"
        assert body["code"] == "scheduler_auth_not_configured"
        assert len(mock_scheduler_oidc) == 0


class TestScheduledCollectionJobExecution:
    """Verify full collection, share message creation, user notification, retries, and concurrency."""

    def test_collect_job_end_to_end_saves_articles_messages_and_notifies_users(
        self,
        app,
        client,
        fake_db,
        mock_scheduler_oidc,
        mock_fcm_send,
        monkeypatch,
    ):
        source_repo = SourceRepository(db=fake_db)
        article_repo = ArticleRepository(db=fake_db)
        share_repo = ShareMessageRepository(db=fake_db)
        device_repo = UserDeviceRepository(db=fake_db)

        enabled_source = source_repo.create(
            name="Enabled RSS Feed",
            url="https://feeds.example.com/rss.xml",
            source_type="rss",
            enabled=True,
        )
        disabled_source = source_repo.create(
            name="Disabled RSS Feed",
            url="https://feeds.example.com/disabled.xml",
            source_type="rss",
            enabled=False,
        )
        failing_source = source_repo.create(
            name="Failing RSS Feed",
            url="https://news.example.org/broken.xml",
            source_type="rss",
            enabled=True,
        )

        # Register two active user devices
        device_repo.upsert_device(
            user_id="user-1",
            fcm_token="fcm-token-user-1-valid-device",
            platform="android",
        )
        device_repo.upsert_device(
            user_id="user-2",
            fcm_token="fcm-token-user-2-valid-device",
            platform="ios",
        )

        def fake_http_open(request_obj, timeout=5.0):
            url = request_obj.full_url
            if url == "https://feeds.example.com/rss.xml":
                return _MockHttpResponse(SAMPLE_RSS_FEED)
            if url == "https://news.example.org/broken.xml":
                raise HTTPError(
                    url=url,
                    code=503,
                    msg="Service Unavailable",
                    hdrs=Message(),
                    fp=None,
                )
            raise AssertionError(f"Unexpected URL fetched: {url}")

        app.config["SOURCE_HTTP_OPENER"] = fake_http_open

        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
        )
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["status"] == "completed"
        assert (
            data["scheduler_service_account"]
            == "moatok-scheduler@test-moatok-project.iam.gserviceaccount.com"
        )
        assert (
            mock_scheduler_oidc[0]["audience"]
            == app.config["SCHEDULER_OIDC_AUDIENCE"]
        )

        summary = data["summary"]
        assert summary["sources_checked"] == 2  # disabled_source skipped
        assert summary["sources_succeeded"] == 1
        assert summary["sources_failed"] == 1
        assert summary["processed"] == 2
        assert summary["new"] == 2
        assert summary["duplicate"] == 0
        assert summary["failed"] == 1
        assert summary["share_messages_created"] == 2
        assert summary["notifications"]["messages_notified"] == 2
        assert summary["notifications"]["sent_count"] == 4  # 2 messages * 2 users
        assert summary["notifications"]["failed_count"] == 0

        # Verify Firestore persistence
        articles = article_repo.list_articles()
        assert len(articles) == 2

        share_messages = share_repo.list_messages(status="pending")
        assert len(share_messages) == 2
        for msg in share_messages:
            assert msg["status"] == "pending"
            assert msg["initial_notification_claimed"] is True
            assert msg["notification_attempts"] == 1
            assert msg["last_notification_sent_count"] == 2
            assert msg["last_notification_status"] == "sent"
            assert msg["kakao_shared"] is False

        # Verify FCM payload is concise and contains no sensitive content
        assert len(mock_fcm_send) == 4
        for fcm_msg in mock_fcm_send:
            assert fcm_msg.data["action"] == "OPEN_SHARE_PREVIEW"
            assert fcm_msg.data["share_message_id"] in {
                m["id"] for m in share_messages
            }
            assert "body" not in fcm_msg.data
            assert "target_url" not in fcm_msg.data

        # Disabled source was never checked
        assert source_repo.get(disabled_source["id"])["last_checked_at"] is None
        assert source_repo.get(enabled_source["id"])["last_checked_at"] is not None

    def test_retry_and_duplicate_requests_are_idempotent(
        self,
        app,
        client,
        fake_db,
        mock_scheduler_oidc,
        mock_fcm_send,
    ):
        source_repo = SourceRepository(db=fake_db)
        article_repo = ArticleRepository(db=fake_db)
        share_repo = ShareMessageRepository(db=fake_db)
        device_repo = UserDeviceRepository(db=fake_db)

        source_repo.create(
            name="Primary RSS Feed",
            url="https://feeds.example.com/rss.xml",
            source_type="rss",
            enabled=True,
        )
        device_repo.upsert_device(
            user_id="user-1",
            fcm_token="fcm-token-user-1-retry-test",
            platform="flutter",
        )

        app.config["SOURCE_HTTP_OPENER"] = (
            lambda req, timeout=5.0: _MockHttpResponse(SAMPLE_RSS_FEED)
        )

        # First run
        resp1 = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
        )
        assert resp1.status_code == 200
        summary1 = resp1.get_json()["summary"]
        assert summary1["new"] == 2
        assert summary1["duplicate"] == 0
        assert summary1["share_messages_created"] == 2
        assert summary1["notifications"]["messages_notified"] == 2
        assert len(mock_fcm_send) == 2

        # Duplicate / retry run with identical feed items
        resp2 = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
        )
        assert resp2.status_code == 200
        summary2 = resp2.get_json()["summary"]
        assert summary2["new"] == 0
        assert summary2["duplicate"] == 2
        assert summary2["share_messages_created"] == 0
        assert summary2["notifications"]["messages_notified"] == 0
        assert summary2["notifications"]["sent_count"] == 0

        # No duplicate articles, share messages, or FCM pushes
        assert len(article_repo.list_articles()) == 2
        assert len(share_repo.list_messages()) == 2
        assert len(mock_fcm_send) == 2

    def test_partial_retry_recovers_missing_share_message_and_notification(
        self,
        app,
        client,
        fake_db,
        mock_scheduler_oidc,
        mock_fcm_send,
    ):
        """Simulate a previous crash where an article was saved before its share message was created."""
        source_repo = SourceRepository(db=fake_db)
        article_repo = ArticleRepository(db=fake_db)
        share_repo = ShareMessageRepository(db=fake_db)
        device_repo = UserDeviceRepository(db=fake_db)

        source = source_repo.create(
            name="Primary RSS Feed",
            url="https://feeds.example.com/rss.xml",
            source_type="rss",
            enabled=True,
        )
        # Pre-populate article 101 without a share message
        article_repo.create(
            source_id=source["id"],
            source_url=source["url"],
            canonical_url="https://feeds.example.com/posts/101",
            stable_id="sched-guid-101",
            title="Scheduled Article One",
            summary="Summary of scheduled article one.",
        )
        device_repo.upsert_device(
            user_id="user-1",
            fcm_token="fcm-token-user-1-partial-retry",
            platform="flutter",
        )

        app.config["SOURCE_HTTP_OPENER"] = (
            lambda req, timeout=5.0: _MockHttpResponse(SAMPLE_RSS_FEED)
        )

        resp = client.post(
            "/internal/jobs/collect",
            headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
        )
        assert resp.status_code == 200
        summary = resp.get_json()["summary"]

        # 1 duplicate article (101) + 1 new article (102), but BOTH get share messages & notifications
        assert summary["new"] == 1
        assert summary["duplicate"] == 1
        assert summary["share_messages_created"] == 2
        assert summary["notifications"]["messages_notified"] == 2
        assert len(share_repo.list_messages()) == 2
        assert len(mock_fcm_send) == 2

    def test_concurrent_job_executions_do_not_duplicate_articles_messages_or_notifications(
        self,
        app,
        fake_db,
        mock_scheduler_oidc,
        mock_fcm_send,
        monkeypatch,
    ):
        source_repo = SourceRepository(db=fake_db)
        article_repo = ArticleRepository(db=fake_db)
        share_repo = ShareMessageRepository(db=fake_db)
        device_repo = UserDeviceRepository(db=fake_db)

        source_repo.create(
            name="Concurrent RSS Feed",
            url="https://feeds.example.com/rss.xml",
            source_type="rss",
            enabled=True,
        )
        device_repo.upsert_device(
            user_id="user-1",
            fcm_token="fcm-token-user-1-concurrent",
            platform="flutter",
        )

        app.config["SOURCE_HTTP_OPENER"] = (
            lambda req, timeout=5.0: _MockHttpResponse(SAMPLE_RSS_FEED)
        )

        def _invoke_job() -> dict[str, Any]:
            with app.test_client() as test_client:
                res = test_client.post(
                    "/internal/jobs/collect",
                    headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
                )
                assert res.status_code == 200
                return res.get_json()["summary"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            summaries = list(pool.map(lambda _: _invoke_job(), range(4)))

        assert sum(s["new"] for s in summaries) == 2
        assert sum(s["share_messages_created"] for s in summaries) == 2
        assert sum(s["notifications"]["messages_notified"] for s in summaries) == 2
        assert len(article_repo.list_articles()) == 2
        assert len(share_repo.list_messages()) == 2
        assert len(mock_fcm_send) == 2
