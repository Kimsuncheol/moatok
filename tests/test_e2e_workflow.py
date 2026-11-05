"""End-to-end workflow and Cloud Run readiness tests.

Covers:
1. Gunicorn PORT environment variable binding and container/repository credential hygiene.
2. Full end-to-end flow:
   - Administrator source creation
   - User FCM device token registration
   - Cloud Scheduler OIDC-authenticated RSS collection
   - Article & share message deduplication across feed items and repeated job runs
   - Firestore persistence in UTC
   - Concise FCM push notifications (observable without implying KakaoTalk sharing)
   - User-initiated KakaoTalk sharing preview and completion (`mark-shared`)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

from app.repositories import (
    ArticleRepository,
    ShareMessageRepository,
    SourceRepository,
    UserDeviceRepository,
)
from app.services.url_validator import SyntheticProbeResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_gunicorn_conf():
    spec = importlib.util.spec_from_file_location(
        "moatok_gunicorn_conf", PROJECT_ROOT / "gunicorn.conf.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E2E_RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Moatok E2E Briefing Feed</title>
    <item>
      <guid>e2e-guid-1</guid>
      <title>Cloud Run Least Privilege Guide</title>
      <link>https://feeds.example.com/articles/cloud-run-iam?utm_source=rss</link>
      <description>Deploy Flask with a dedicated service account and OIDC scheduler auth.</description>
      <pubDate>Thu, 05 Nov 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <guid>e2e-guid-1</guid>
      <title>Cloud Run Least Privilege Guide (Duplicate GUID in Same Feed)</title>
      <link>https://feeds.example.com/articles/cloud-run-iam?utm_medium=mirror</link>
      <description>Duplicate item with identical stable GUID should be deduplicated.</description>
      <pubDate>Thu, 05 Nov 2026 08:05:00 GMT</pubDate>
    </item>
    <item>
      <guid>e2e-guid-2</guid>
      <title>User-Initiated KakaoTalk Sharing in Flutter</title>
      <link>https://feeds.example.com/articles/flutter-kakao-share</link>
      <description>Users review and trigger KakaoTalk sharing directly in the Flutter app.</description>
      <pubDate>Thu, 05 Nov 2026 09:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_gunicorn_config_and_dockerfile_respect_port_and_exclude_credentials():
    """Verify Gunicorn respects PORT and repository/container configs exclude credentials."""
    gunicorn_conf = _load_gunicorn_conf()
    assert gunicorn_conf.resolve_bind_address({}) == "0.0.0.0:8080"
    assert gunicorn_conf.resolve_bind_address({"PORT": "9090"}) == "0.0.0.0:9090"
    assert gunicorn_conf.resolve_bind_address({"PORT": " 8081 "}) == "0.0.0.0:8081"

    with pytest.raises(ValueError):
        gunicorn_conf.resolve_bind_address({"PORT": "not-a-port"})

    with pytest.raises(ValueError):
        gunicorn_conf.resolve_bind_address({"PORT": "70000"})

    dockerfile_text = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "gunicorn" in dockerfile_text
    assert "${PORT:-8080}" in dockerfile_text
    assert "USER appuser" in dockerfile_text

    dockerignore_text = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    for pattern in (".env", "*service-account*.json", "*credentials*.json", "*.pem"):
        assert pattern in dockerignore_text


def test_full_end_to_end_collection_deduplication_persistence_notification_and_sharing(
    app,
    client,
    fake_db,
    mock_firebase_auth,
    mock_fcm_send,
    monkeypatch,
):
    """Execute the complete 5-stage E2E workflow from source creation to user-initiated sharing."""
    # Mock Cloud Scheduler OIDC verification
    monkeypatch.setattr(
        "app.auth.verify_scheduler_oidc_token",
        lambda token, audience=None: {
            "iss": "https://accounts.google.com",
            "sub": "scheduler-sa-sub",
            "email": app.config["SCHEDULER_SERVICE_ACCOUNT_EMAIL"],
            "email_verified": True,
            "aud": audience,
        },
    )

    app.config["SOURCE_HTTP_OPENER"] = lambda req, timeout=5.0: SyntheticProbeResponse(
        status=200,
        body=E2E_RSS_FEED,
        headers={"Content-Type": "application/rss+xml; charset=utf-8"},
    )

    # -------------------------------------------------------------------------
    # Stage 1: Admin registers an RSS content source & User registers FCM device
    # -------------------------------------------------------------------------
    create_source_resp = client.post(
        "/api/v1/admin/sources",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={
            "name": "Moatok E2E Feed",
            "url": "https://feeds.example.com/e2e.xml",
            "source_type": "rss",
            "enabled": True,
        },
    )
    assert create_source_resp.status_code == 201
    source_id = create_source_resp.get_json()["source"]["id"]

    register_device_resp = client.post(
        "/api/v1/devices/fcm-token",
        headers={"Authorization": "Bearer valid-token-user-1"},
        json={
            "fcm_token": "e2e-user-1-flutter-fcm-token",
            "device_id": "device-flutter-ios-1",
            "platform": "ios",
        },
    )
    assert register_device_resp.status_code == 200

    # -------------------------------------------------------------------------
    # Stage 2: Cloud Scheduler triggers collection & deduplicates feed items
    # -------------------------------------------------------------------------
    collect_resp_1 = client.post(
        "/internal/jobs/collect",
        headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
    )
    assert collect_resp_1.status_code == 200
    summary_1 = collect_resp_1.get_json()["summary"]
    assert summary_1["sources_checked"] == 1
    assert summary_1["sources_succeeded"] == 1
    assert summary_1["processed"] == 3  # 2 unique + 1 in-feed duplicate
    assert summary_1["new"] == 2
    assert summary_1["duplicate"] == 1
    assert summary_1["failed"] == 0
    assert summary_1["share_messages_created"] == 2
    assert summary_1["notifications"]["messages_notified"] == 2
    assert summary_1["notifications"]["sent_count"] == 2

    # Repeated Cloud Scheduler trigger (retry / next cron tick with same feed)
    collect_resp_2 = client.post(
        "/internal/jobs/collect",
        headers={"Authorization": "Bearer valid-scheduler-oidc-token"},
    )
    assert collect_resp_2.status_code == 200
    summary_2 = collect_resp_2.get_json()["summary"]
    assert summary_2["processed"] == 3
    assert summary_2["new"] == 0
    assert summary_2["duplicate"] == 3
    assert summary_2["share_messages_created"] == 0
    assert summary_2["notifications"]["messages_notified"] == 0
    assert summary_2["notifications"]["sent_count"] == 0

    # -------------------------------------------------------------------------
    # Stage 3: Verify Firestore persistence across all 4 collections
    # -------------------------------------------------------------------------
    source_repo = SourceRepository(db=fake_db)
    article_repo = ArticleRepository(db=fake_db)
    share_repo = ShareMessageRepository(db=fake_db)
    device_repo = UserDeviceRepository(db=fake_db)

    persisted_source = source_repo.get(source_id)
    assert persisted_source is not None
    assert persisted_source["last_checked_at"] is not None

    persisted_articles = article_repo.list_articles(source_id=source_id)
    assert len(persisted_articles) == 2

    persisted_messages = share_repo.list_messages(status="pending")
    assert len(persisted_messages) == 2

    persisted_devices = device_repo.list_devices("user-1", enabled_only=True)
    assert len(persisted_devices) == 1
    assert persisted_devices[0]["fcm_token"] == "e2e-user-1-flutter-fcm-token"

    # -------------------------------------------------------------------------
    # Stage 4: Verify FCM notification payload & observability (not Kakao proof)
    # -------------------------------------------------------------------------
    assert len(mock_fcm_send) == 2  # Exactly 2 notifications from run 1, 0 from run 2
    notified_msg_id = mock_fcm_send[0].data["share_message_id"]
    assert mock_fcm_send[0].data["action"] == "OPEN_SHARE_PREVIEW"
    assert "body" not in mock_fcm_send[0].data
    assert "target_url" not in mock_fcm_send[0].data

    # Admin inspects and optionally edits the pending share message before user shares
    admin_edit_resp = client.patch(
        f"/api/v1/admin/share-messages/{notified_msg_id}",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={"title": "Cloud Run Least Privilege Guide (Reviewed)"},
    )
    assert admin_edit_resp.status_code == 200
    assert (
        admin_edit_resp.get_json()["share_message"]["title"]
        == "Cloud Run Least Privilege Guide (Reviewed)"
    )

    # -------------------------------------------------------------------------
    # Stage 5: User previews message in Flutter & marks shared after Kakao SDK
    # -------------------------------------------------------------------------
    preview_resp = client.get(
        f"/api/v1/messages/{notified_msg_id}",
        headers={"Authorization": "Bearer valid-token-user-1"},
    )
    assert preview_resp.status_code == 200
    preview_msg = preview_resp.get_json()["message"]
    assert preview_msg["id"] == notified_msg_id
    assert preview_msg["status"] == "pending"
    assert preview_msg["kakao_shared"] is False
    assert preview_msg["title"] == "Cloud Run Least Privilege Guide (Reviewed)"

    mark_shared_resp = client.post(
        f"/api/v1/messages/{notified_msg_id}/mark-shared",
        headers={"Authorization": "Bearer valid-token-user-1"},
        json={"share_channel": "kakaotalk_flutter_sdk"},
    )
    assert mark_shared_resp.status_code == 200
    shared_msg = mark_shared_resp.get_json()["message"]
    assert shared_msg["id"] == notified_msg_id
    assert shared_msg["status"] == "shared"
    assert shared_msg["kakao_shared"] is True
    assert shared_msg["shared_by_user_id"] == "user-1"
    assert shared_msg["last_share_channel"] == "kakaotalk_flutter_sdk"
    assert shared_msg["shared_by_user_at"] is not None
