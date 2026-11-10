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


def test_record_share_attempt_does_not_mark_as_delivered(client, mock_firebase_auth):
    headers_user1 = {"Authorization": "Bearer valid-token-user-1"}

    # 1. Create a pending message
    create_res = client.post(
        "/api/v1/messages",
        headers=headers_user1,
        json={
            "title": "공유 시도 테스트 아티클",
            "items": [{"title": "카카오톡 공유 시작"}],
            "notify_user": False,
        },
    )
    assert create_res.status_code == 201
    msg_id = create_res.get_json()["message"]["id"]

    # 2. Record first share attempt via Kakao JS SDK
    attempt1_res = client.post(
        f"/api/v1/messages/{msg_id}/share-attempt",
        headers=headers_user1,
        json={"channel": "kakao_sdk"},
    )
    assert attempt1_res.status_code == 200
    data1 = attempt1_res.get_json()
    assert data1["recorded"] is True
    assert data1["channel"] == "kakao_sdk"
    assert data1["share_attempt_count"] == 1
    # Architectural boundary: status is NOT shared, kakao_shared is NOT True
    assert data1["status"] in ("pending", "ready_to_share", "notified")
    assert data1["status"] not in ("shared", "shared_by_user")
    assert data1["kakao_shared"] is False

    # 3. Record second share attempt (e.g. user retries with web_share fallback)
    attempt2_res = client.post(
        f"/api/v1/messages/{msg_id}/share-attempt",
        headers=headers_user1,
        json={"channel": "web_share"},
    )
    assert attempt2_res.status_code == 200
    data2 = attempt2_res.get_json()
    assert data2["share_attempt_count"] == 2
    assert data2["channel"] == "web_share"
    assert data2["kakao_shared"] is False

    # Verify message detail still reflects pending status
    get_res = client.get(f"/api/v1/messages/{msg_id}", headers=headers_user1)
    assert get_res.status_code == 200
    msg_detail = get_res.get_json()["message"]
    assert msg_detail.get("kakao_shared") is not True
    assert msg_detail.get("share_attempt_count") == 2
    assert msg_detail.get("last_share_attempt_channel") == "web_share"


def test_fetched_import_is_persistent_deduplicated_and_owned(client, mock_firebase_auth):
    headers = {'Authorization': 'Bearer valid-token-user-1'}
    payload = {'title': 'Article', 'body': 'Full article text', 'target_url': 'https://example.com/article', 'source_name': 'Source', 'endpoint_id': 'ep'}
    assert client.post('/api/v1/messages/imports', json=payload).status_code == 401
    first = client.post('/api/v1/messages/imports', headers=headers, json=payload)
    assert first.status_code == 200
    message = first.json['message']
    again = client.post('/api/v1/messages/imports', headers=headers, json=payload)
    assert again.json['message']['id'] == message['id']
    listed = client.get('/api/v1/messages?status=pending', headers=headers).json['messages']
    assert [m['id'] for m in listed] == [message['id']]
    client.post('/api/v1/messages/' + message['id'] + '/mark-shared', headers=headers, json={'share_channel': 'test'})
    assert client.post('/api/v1/messages/imports', headers=headers, json=payload).json['message']['status'] == 'shared_by_user'
    other = client.post('/api/v1/messages/imports', headers={'Authorization': 'Bearer valid-token-user-2'}, json=payload)
    assert other.json['message']['id'] != message['id']
