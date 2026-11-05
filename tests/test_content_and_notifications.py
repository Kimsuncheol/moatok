"""Automated tests for authentication, content collection, Firestore storage, and FCM notifications."""

from __future__ import annotations


def test_unauthorized_request_rejected(client):
    response = client.get("/api/v1/messages")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_register_fcm_token_and_collect_content_with_notification(
    client, mock_firebase_auth, mock_fcm_send
):
    headers = {"Authorization": "Bearer valid-token-user-1"}

    # 1. Register user's Flutter FCM device token
    reg_res = client.post(
        "/api/v1/devices/fcm-token",
        headers=headers,
        json={"fcm_token": "flutter-device-token-abc", "platform": "flutter_ios"},
    )
    assert reg_res.status_code == 200
    assert reg_res.get_json()["device"]["token_count"] == 1

    # 2. Collect content & prepare shareable message
    create_res = client.post(
        "/api/v1/messages",
        headers=headers,
        json={
            "title": "오늘의 IT 주요 뉴스 모음",
            "intro_note": "팀원들과 공유하기 좋은 아침 브리핑입니다.",
            "target_audience_hint": "개발팀 단톡방",
            "tags": ["AI", "Cloud"],
            "items": [
                {
                    "title": "Python 3.12 성능 개선 정리",
                    "summary": "인터프리터 최적화 및 타입 문법 개선",
                    "url": "https://example.com/python-312",
                    "source_name": "TechBlog",
                },
                {
                    "title": "Flutter 카카오톡 공유 SDK 활용 팁",
                    "summary": "사용자 주도 카카오톡 메시지 공유 플로우 구현",
                    "url": "https://example.com/flutter-kakao-share",
                    "source_name": "MobileWeekly",
                },
            ],
            "notify_user": True,
        },
    )
    assert create_res.status_code == 201
    body = create_res.get_json()

    created_msg = body["message"]
    assert created_msg["user_id"] == "user-1"
    assert created_msg["sharing_mode"] == "user_initiated_flutter"
    assert created_msg["status"] == "notified"
    assert (
        created_msg["kakao_share_payload"]["requires_user_action_in_flutter"] is True
    )
    assert "Python 3.12 성능 개선 정리" in created_msg["formatted_text"]

    # Verify FCM push notification was dispatched to the registered token
    assert body["notification"]["sent_count"] == 1
    assert len(mock_fcm_send) == 1
    assert mock_fcm_send[0].token == "flutter-device-token-abc"
    assert mock_fcm_send[0].data["action"] == "OPEN_SHARE_PREVIEW"
    assert mock_fcm_send[0].data["message_id"] == created_msg["id"]


def test_list_get_and_mark_shared_by_user(
    client, mock_firebase_auth, mock_fcm_send
):
    headers_user1 = {"Authorization": "Bearer valid-token-user-1"}
    headers_user2 = {"Authorization": "Bearer valid-token-user-2"}

    # Create a message as user-1 without registered FCM token
    create_res = client.post(
        "/api/v1/messages",
        headers=headers_user1,
        json={
            "title": "주간 디자인 레퍼런스",
            "items": [
                {
                    "title": "모바일 온보딩 UI 사례",
                    "url": "https://example.com/onboarding-ui",
                }
            ],
            "notify_user": False,
        },
    )
    assert create_res.status_code == 201
    msg_id = create_res.get_json()["message"]["id"]

    # List messages for user-1
    list_res = client.get("/api/v1/messages", headers=headers_user1)
    assert list_res.status_code == 200
    assert list_res.get_json()["count"] == 1

    # Ensure user-2 cannot read user-1's prepared message
    forbidden_res = client.get(
        f"/api/v1/messages/{msg_id}", headers=headers_user2
    )
    assert forbidden_res.status_code == 404

    # Mark message as shared after user initiates KakaoTalk sharing in Flutter
    shared_res = client.post(
        f"/api/v1/messages/{msg_id}/mark-shared",
        headers=headers_user1,
        json={"share_channel": "kakaotalk_flutter_sdk"},
    )
    assert shared_res.status_code == 200
    updated_msg = shared_res.get_json()["message"]
    assert updated_msg["status"] == "shared_by_user"
    assert updated_msg["shared_by_user_at"] is not None


def test_internal_api_key_ingestion(client, mock_fcm_send):
    res = client.post(
        "/api/v1/messages",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        json={
            "user_id": "user-1",
            "title": "스케줄러 수집 뉴스",
            "items": [{"title": "클라우드 보안 가이드"}],
            "notify_user": False,
        },
    )
    assert res.status_code == 201
    assert res.get_json()["message"]["user_id"] == "user-1"
