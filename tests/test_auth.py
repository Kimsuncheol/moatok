"""Automated tests for Firebase Authentication, custom claim admin authorization, and error handling."""

from __future__ import annotations

from firebase_admin import auth as firebase_auth
import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/devices/fcm-token"),
        ("GET", "/api/v1/messages"),
        ("POST", "/api/v1/messages"),
        ("GET", "/api/v1/messages/msg-123"),
        ("POST", "/api/v1/messages/msg-123/notify"),
        ("POST", "/api/v1/messages/msg-123/mark-shared"),
        ("GET", "/api/v1/admin/messages"),
        ("POST", "/api/v1/admin/users/user-1/claims"),
    ],
)
def test_missing_token_returns_consistent_401_json(client, method, path):
    """All protected endpoints must reject requests missing a Bearer token with a consistent 401 JSON error."""
    response = client.open(path, method=method)
    assert response.status_code == 401

    payload = response.get_json()
    assert payload["error"] == "unauthorized"
    assert payload["code"] == "missing_token"
    assert "Missing" in payload["message"]


@pytest.mark.parametrize(
    "auth_header,expected_code",
    [
        ("Bearer", "missing_token"),
        ("Bearer    ", "missing_token"),
        ("Basic dXNlcjpwYXNz", "invalid_token"),
        ("Token some-token", "invalid_token"),
        ("Bearer token-part-1 token-part-2", "invalid_token"),
    ],
)
def test_malformed_authorization_header_returns_401_json(
    client, auth_header, expected_code
):
    """Malformed Authorization headers must return a consistent 401 JSON error."""
    response = client.get(
        "/api/v1/messages",
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 401

    payload = response.get_json()
    assert payload["error"] == "unauthorized"
    assert payload["code"] == expected_code
    assert isinstance(payload["message"], str) and payload["message"]


def test_expired_firebase_token_returns_consistent_401_json(client, mock_firebase_auth):
    """Expired Firebase ID tokens must return 401 with code='token_expired'."""
    response = client.get(
        "/api/v1/messages",
        headers={"Authorization": "Bearer expired-token"},
    )
    assert response.status_code == 401

    payload = response.get_json()
    assert payload == {
        "error": "unauthorized",
        "code": "token_expired",
        "message": "Firebase ID token has expired.",
    }


def test_invalid_firebase_token_returns_consistent_401_json(client, mock_firebase_auth):
    """Invalid Firebase ID tokens must return 401 with code='invalid_token'."""
    response = client.get(
        "/api/v1/messages",
        headers={"Authorization": "Bearer forged-or-corrupted-token"},
    )
    assert response.status_code == 401

    payload = response.get_json()
    assert payload == {
        "error": "unauthorized",
        "code": "invalid_token",
        "message": "Invalid Firebase ID token.",
    }


def test_revoked_and_disabled_tokens_return_consistent_401_json(
    client, mock_firebase_auth
):
    """Revoked tokens and disabled user tokens must return 401 with specific error codes."""
    revoked_res = client.get(
        "/api/v1/messages",
        headers={"Authorization": "Bearer revoked-token"},
    )
    assert revoked_res.status_code == 401
    assert revoked_res.get_json()["error"] == "unauthorized"
    assert revoked_res.get_json()["code"] == "token_revoked"

    disabled_res = client.get(
        "/api/v1/messages",
        headers={"Authorization": "Bearer disabled-user-token"},
    )
    assert disabled_res.status_code == 401
    assert disabled_res.get_json()["error"] == "unauthorized"
    assert disabled_res.get_json()["code"] == "user_disabled"


def test_verify_firebase_token_calls_firebase_admin_sdk(client, monkeypatch):
    """Verify that verify_firebase_token delegates to firebase_admin.auth.verify_id_token."""
    captured_calls: list[tuple[str, bool]] = []

    def _fake_verify_id_token(id_token: str, check_revoked: bool = False):
        captured_calls.append((id_token, check_revoked))
        return {"uid": "sdk-user-1", "email": "sdk@example.com"}

    monkeypatch.setattr(firebase_auth, "verify_id_token", _fake_verify_id_token)

    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer raw-firebase-jwt"},
    )
    assert res.status_code == 200
    assert captured_calls == [("raw-firebase-jwt", False)]
    assert res.get_json()["user"] == {
        "uid": "sdk-user-1",
        "email": "sdk@example.com",
        "role": "user",
        "is_admin": False,
    }


def test_authenticated_regular_user_profile_and_access(client, mock_firebase_auth):
    """An authenticated standard user receives role='user' and can access user endpoints."""
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer valid-token-user-1"},
    )
    assert res.status_code == 200
    assert res.get_json()["user"] == {
        "uid": "user-1",
        "email": "user1@example.com",
        "role": "user",
        "is_admin": False,
    }


def test_administrator_authorized_via_verified_custom_claims(
    client, mock_firebase_auth, mock_fcm_send
):
    """A user with verified Firebase custom claim {'admin': True} is authorized for admin endpoints."""
    admin_headers = {"Authorization": "Bearer valid-token-admin"}
    user1_headers = {"Authorization": "Bearer valid-token-user-1"}
    user2_headers = {"Authorization": "Bearer valid-token-user-2"}

    # 1. Verify /api/v1/auth/me reflects verified admin custom claim
    me_res = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me_res.status_code == 200
    assert me_res.get_json()["user"] == {
        "uid": "admin-1",
        "email": "admin@example.com",
        "role": "admin",
        "is_admin": True,
    }

    # 2. User-1 and User-2 each create a message
    client.post(
        "/api/v1/messages",
        headers=user1_headers,
        json={
            "title": "User 1 Message",
            "items": [{"title": "Item A"}],
            "notify_user": False,
        },
    )
    client.post(
        "/api/v1/messages",
        headers=user2_headers,
        json={
            "title": "User 2 Message",
            "items": [{"title": "Item B"}],
            "notify_user": False,
        },
    )

    # 3. Admin can list all messages across all users via /api/v1/admin/messages
    admin_list_res = client.get("/api/v1/admin/messages", headers=admin_headers)
    assert admin_list_res.status_code == 200
    assert admin_list_res.get_json()["count"] == 2

    # 4. Admin can also create a message on behalf of user-1
    admin_create_res = client.post(
        "/api/v1/messages",
        headers=admin_headers,
        json={
            "user_id": "user-1",
            "title": "Admin Curated Brief",
            "items": [{"title": "Security Advisory"}],
            "notify_user": False,
        },
    )
    assert admin_create_res.status_code == 201
    created_msg = admin_create_res.get_json()["message"]
    assert created_msg["user_id"] == "user-1"

    # 5. Admin can retrieve user-1's message directly
    admin_get_res = client.get(
        f"/api/v1/messages/{created_msg['id']}", headers=admin_headers
    )
    assert admin_get_res.status_code == 200
    assert admin_get_res.get_json()["message"]["id"] == created_msg["id"]


def test_client_supplied_roles_are_never_accepted_for_authorization(
    client, mock_firebase_auth
):
    """Client-supplied roles in headers, query params, or JSON body must never grant admin access."""
    SpoofedHeaders = {
        "Authorization": "Bearer valid-token-user-1",
        "X-User-Role": "admin",
        "X-Role": "admin",
        "X-Admin": "true",
    }

    # 1. Spoofing role via headers & query params on /api/v1/auth/me does not elevate role
    me_res = client.get(
        "/api/v1/auth/me?role=admin&admin=true&is_admin=true",
        headers=SpoofedHeaders,
    )
    assert me_res.status_code == 200
    assert me_res.get_json()["user"]["role"] == "user"
    assert me_res.get_json()["user"]["is_admin"] is False

    # 2. Non-admin cannot access /api/v1/admin/messages even with spoofed headers/query params
    admin_messages_res = client.get(
        "/api/v1/admin/messages?role=admin&admin=true",
        headers=SpoofedHeaders,
    )
    assert admin_messages_res.status_code == 403
    assert admin_messages_res.get_json() == {
        "error": "forbidden",
        "code": "admin_required",
        "message": "Administrator privileges required.",
    }

    # 3. Non-admin cannot assign custom claims even if supplying role/admin in JSON body
    claims_res = client.post(
        "/api/v1/admin/users/user-1/claims",
        headers=SpoofedHeaders,
        json={
            "admin": True,
            "role": "admin",
            "is_admin": True,
            "claims": {"admin": True},
        },
    )
    assert claims_res.status_code == 403
    assert claims_res.get_json()["error"] == "forbidden"
    assert claims_res.get_json()["code"] == "admin_required"

    # 4. Non-admin cannot create a message for another user by passing role='admin' in body
    cross_user_create_res = client.post(
        "/api/v1/messages",
        headers=SpoofedHeaders,
        json={
            "user_id": "user-2",
            "role": "admin",
            "admin": True,
            "is_admin": True,
            "title": "Spoofed Message",
            "items": [{"title": "Attempted spoof"}],
            "notify_user": False,
        },
    )
    assert cross_user_create_res.status_code == 403
    assert cross_user_create_res.get_json()["error"] == "forbidden"
    assert cross_user_create_res.get_json()["code"] == "admin_required"

    # 5. Non-admin cannot list another user's messages via query parameter
    cross_user_list_res = client.get(
        "/api/v1/messages?user_id=user-2&role=admin",
        headers=SpoofedHeaders,
    )
    assert cross_user_list_res.status_code == 403
    assert cross_user_list_res.get_json()["error"] == "forbidden"
    assert cross_user_list_res.get_json()["code"] == "admin_required"


def test_admin_can_assign_admin_custom_claim(client, mock_firebase_auth, monkeypatch):
    """A verified administrator can assign or revoke the 'admin' custom claim via Firebase Admin SDK."""
    recorded_claims: list[tuple[str, dict]] = []

    def _mock_set_custom_user_claims(uid: str, custom_claims: dict):
        recorded_claims.append((uid, custom_claims))

    monkeypatch.setattr(
        firebase_auth, "set_custom_user_claims", _mock_set_custom_user_claims
    )

    res = client.post(
        "/api/v1/admin/users/user-2/claims",
        headers={"Authorization": "Bearer valid-token-admin"},
        json={"admin": True},
    )
    assert res.status_code == 200
    assert res.get_json() == {
        "status": "updated",
        "uid": "user-2",
        "custom_claims": {"admin": True},
    }
    assert recorded_claims == [("user-2", {"admin": True})]


def test_health_endpoint_remains_public_without_authentication(client):
    """The GET /health endpoint must remain publicly accessible without any Authorization header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
