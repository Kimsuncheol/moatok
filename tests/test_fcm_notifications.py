"""Automated tests for FCM device registration, concise pending share message notifications,
invalid/expired token handling, and observable notification tracking."""

from __future__ import annotations

from firebase_admin import exceptions as firebase_exceptions
from firebase_admin import messaging

from app.repositories import ShareMessageRepository, UserDeviceRepository
from app.services.notification_service import notify_pending_share_message
from app.services.share_message_generator import RuleBasedShareMessageGenerator


def test_register_and_update_device_token_for_authenticated_user(
    client, fake_db, mock_firebase_auth
):
    """Authenticated user can register a device token and update it in place by device_id."""
    headers = {"Authorization": "Bearer valid-token-user-1"}
    device_repo = UserDeviceRepository(db=fake_db)

    # 1. Register initial device token with explicit device_id
    reg_res = client.post(
        "/api/v1/devices/fcm-token",
        headers=headers,
        json={
            "device_id": "dev_iphone_15",
            "fcm_token": "initial-fcm-token-v1",
            "platform": "flutter_ios",
        },
    )
    assert reg_res.status_code == 200
    dev_info = reg_res.get_json()["device"]
    assert dev_info["user_id"] == "user-1"
    assert dev_info["device_id"] == "dev_iphone_15"
    assert dev_info["token_count"] == 1

    stored_v1 = device_repo.get_device("user-1", "dev_iphone_15")
    assert stored_v1["fcm_token"] == "initial-fcm-token-v1"
    created_at_v1 = stored_v1["created_at"]

    # 2. Rotate / update token on the same device_id
    update_res = client.put(
        "/api/v1/devices/fcm-token",
        headers=headers,
        json={
            "device_id": "dev_iphone_15",
            "fcm_token": "rotated-fcm-token-v2",
            "platform": "flutter_ios",
        },
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["device"]["token_count"] == 1

    stored_v2 = device_repo.get_device("user-1", "dev_iphone_15")
    assert stored_v2["fcm_token"] == "rotated-fcm-token-v2"
    assert stored_v2["created_at"] == created_at_v1
    assert len(device_repo.list_devices("user-1")) == 1


def test_concise_notification_payload_excludes_sensitive_content_and_tracks_attempts_without_kakao_share_proof(
    client, fake_db, mock_firebase_auth, mock_fcm_send
):
    """Notifications must include share_message_id, exclude sensitive content, and never mark KakaoTalk sharing complete."""
    user_headers = {"Authorization": "Bearer valid-token-user-1"}
    admin_headers = {"Authorization": "Bearer valid-token-admin"}

    # Register device for user-1
    client.post(
        "/api/v1/devices/fcm-token",
        headers=user_headers,
        json={"fcm_token": "valid-fcm-token-user1", "platform": "flutter_android"},
    )

    # Generate a new pending share message containing sensitive-looking article body/details
    share_repo = ShareMessageRepository(db=fake_db)
    generator = RuleBasedShareMessageGenerator(share_repo=share_repo)
    pending_msg = generator.generate_for_article(
        {
            "id": "art_sensitive_test",
            "title": "Internal Security Bulletin",
            "summary": "CONFIDENTIAL_SUMMARY_TEXT_DO_NOT_LEAK_IN_PUSH",
            "canonical_url": "https://example.com/security/bulletin-42",
        }
    )
    msg_id = pending_msg["id"]
    assert pending_msg["status"] == "pending"

    # Dispatch notification via protected endpoint
    notify_res = client.post(
        f"/api/v1/admin/share-messages/{msg_id}/notify",
        headers=admin_headers,
        json={"user_id": "user-1"},
    )
    assert notify_res.status_code == 200
    body = notify_res.get_json()

    # 1. Verify concise FCM message was sent with share_message_id and NO sensitive content
    assert len(mock_fcm_send) == 1
    sent_fcm = mock_fcm_send[0]
    assert sent_fcm.token == "valid-fcm-token-user1"
    assert sent_fcm.data["share_message_id"] == msg_id
    assert sent_fcm.data["message_id"] == msg_id
    assert sent_fcm.data["action"] == "OPEN_SHARE_PREVIEW"

    # Verify sensitive fields/content are NOT in data or notification text
    serialized_data = str(sent_fcm.data)
    notification_text = f"{sent_fcm.notification.title} {sent_fcm.notification.body}"
    for forbidden in (
        "CONFIDENTIAL_SUMMARY_TEXT_DO_NOT_LEAK_IN_PUSH",
        "https://example.com/security/bulletin-42",
        "user1@example.com",
        "user-1",
        "valid-fcm-token-user1",
    ):
        assert forbidden not in serialized_data
        assert forbidden not in notification_text

    # 2. Verify notification attempt is observable, but NOT treated as proof of KakaoTalk sharing
    notif_summary = body["notification"]
    assert notif_summary["sent_count"] == 1
    assert notif_summary["failed_count"] == 0
    assert notif_summary["notification_attempts"] == 1
    assert notif_summary["notification_status"] == "sent"
    assert notif_summary["kakao_shared"] is False
    assert notif_summary["share_message_status"] == "pending"

    stored_msg = share_repo.get(msg_id)
    assert stored_msg["status"] == "pending"
    assert stored_msg["notification_attempts"] == 1
    assert stored_msg["last_notification_status"] == "sent"
    assert stored_msg["last_notification_attempt_at"] is not None
    assert stored_msg["last_notified_at"] is not None
    assert stored_msg["kakao_shared"] is False
    assert stored_msg["shared_by_user_at"] is None


def test_invalid_and_expired_device_tokens_are_handled_and_deactivated(
    fake_db, monkeypatch
):
    """Expired (UnregisteredError) and invalid (InvalidArgumentError) tokens are deactivated while valid tokens succeed."""
    device_repo = UserDeviceRepository(db=fake_db)
    share_repo = ShareMessageRepository(db=fake_db)

    # Register 3 devices for user-1: 1 expired, 1 invalid, 1 valid
    dev_expired = device_repo.upsert_device(
        "user-1",
        device_id="dev_expired",
        fcm_token="expired-fcm-token",
        platform="flutter_ios",
    )
    dev_invalid = device_repo.upsert_device(
        "user-1",
        device_id="dev_invalid",
        fcm_token="malformed-fcm-token",
        platform="flutter_android",
    )
    dev_valid = device_repo.upsert_device(
        "user-1",
        device_id="dev_valid",
        fcm_token="healthy-fcm-token",
        platform="flutter_ios",
    )

    generator = RuleBasedShareMessageGenerator(share_repo=share_repo)
    pending_msg = generator.generate_for_article(
        {
            "id": "art_token_cleanup",
            "title": "Token Cleanup Test",
            "summary": "Testing invalid/expired FCM token deactivation.",
            "canonical_url": "https://example.com/articles/token-cleanup",
        }
    )

    attempted_tokens: list[str] = []

    def _mock_send(message):
        attempted_tokens.append(message.token)
        if message.token == "expired-fcm-token":
            raise messaging.UnregisteredError("Token is no longer registered")
        if message.token == "malformed-fcm-token":
            raise firebase_exceptions.InvalidArgumentError(
                "The registration token is not a valid FCM registration token"
            )
        return "projects/test-moatok-project/messages/msg-ok-1"

    monkeypatch.setattr("firebase_admin.messaging.send", _mock_send)

    # First notification dispatch: 1 sent, 2 failed (both invalid/expired and deactivated)
    result1 = notify_pending_share_message(
        pending_msg,
        user_id="user-1",
        share_repo=share_repo,
        device_repo=device_repo,
    )
    assert result1["sent_count"] == 1
    assert result1["failed_count"] == 2
    assert result1["invalid_token_count"] == 2
    assert set(result1["deactivated_device_ids"]) == {
        dev_expired["device_id"],
        dev_invalid["device_id"],
    }
    assert result1["notification_status"] == "partial_failure"
    assert result1["notification_attempts"] == 1
    assert result1["kakao_shared"] is False

    # Verify expired and invalid devices are now disabled in Firestore
    assert device_repo.get_device("user-1", "dev_expired")["enabled"] is False
    assert device_repo.get_device("user-1", "dev_invalid")["enabled"] is False
    assert device_repo.get_device("user-1", "dev_valid")["enabled"] is True

    # Second notification dispatch: only the remaining active healthy token is contacted
    attempted_tokens.clear()
    result2 = notify_pending_share_message(
        pending_msg,
        user_id="user-1",
        share_repo=share_repo,
        device_repo=device_repo,
    )
    assert attempted_tokens == ["healthy-fcm-token"]
    assert result2["sent_count"] == 1
    assert result2["failed_count"] == 0
    assert result2["invalid_token_count"] == 0
    assert result2["notification_status"] == "sent"
    assert result2["notification_attempts"] == 2
    assert result2["kakao_shared"] is False
