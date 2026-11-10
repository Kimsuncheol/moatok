"""Endpoints for content collection, shareable message retrieval, and FCM notification triggers.

Important:
This backend never posts directly to KakaoTalk Open Chat rooms.
It prepares shareable messages in Firestore and sends push notifications via FCM
so the user can review and initiate KakaoTalk sharing from the Flutter app.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_auth, require_auth_or_internal_key
from app.models import ValidationError
from app.services.content_service import (
    create_shareable_message,
    get_shareable_message,
    list_shareable_messages,
    record_user_share_attempt,
    record_user_share_event,
)
from app.services.notification_service import notify_user_message_ready

content_bp = Blueprint("content", __name__, url_prefix="/api/v1/messages")


@content_bp.post("")
@require_auth_or_internal_key
def collect_and_prepare_message():
    """Collect content items, store a shareable message in Firestore, and optionally notify via FCM."""
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Request body must be valid JSON.",
                }
            ),
            400,
        )

    is_privileged = bool(
        g.current_user.get("is_admin") or g.current_user.get("is_internal")
    )
    authenticated_uid = g.current_user.get("uid")
    requested_uid = str(payload.get("user_id") or "").strip()

    if not is_privileged:
        if requested_uid and requested_uid != authenticated_uid:
            return (
                jsonify(
                    {
                        "error": "forbidden",
                        "code": "admin_required",
                        "message": "Only administrators can create messages for another user.",
                    }
                ),
                403,
            )
        target_payload = {**payload, "user_id": authenticated_uid}
        default_uid = authenticated_uid
    else:
        target_payload = payload
        default_uid = None if g.current_user.get("is_internal") else authenticated_uid

    try:
        created_message = create_shareable_message(
            payload=target_payload, default_user_id=default_uid
        )
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    notify_requested = bool(payload.get("notify_user", True))
    notification_result = None
    if notify_requested:
        notification_result = notify_user_message_ready(created_message)
        if notification_result.get("sent_count", 0) > 0:
            created_message["status"] = "notified"

    return (
        jsonify(
            {
                "message": created_message,
                "notification": notification_result,
            }
        ),
        201,
    )


@content_bp.get("")
@require_auth
def list_user_messages():
    """List prepared shareable messages for the authenticated Flutter user."""
    authenticated_uid = g.current_user["uid"]
    requested_uid = (request.args.get("user_id") or "").strip()

    if requested_uid and requested_uid != authenticated_uid:
        if g.current_user.get("is_admin") is not True:
            return (
                jsonify(
                    {
                        "error": "forbidden",
                        "code": "admin_required",
                        "message": "Only administrators can list another user's messages.",
                    }
                ),
                403,
            )
        user_id = requested_uid
    else:
        user_id = authenticated_uid

    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Query parameter 'limit' must be an integer.",
                }
            ),
            400,
        )

    try:
        messages = list_shareable_messages(user_id=user_id, status=status, limit=limit)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    return jsonify({"messages": messages, "count": len(messages)}), 200


@content_bp.get("/<string:message_id>")
@require_auth
def get_single_message(message_id: str):
    """Fetch a single prepared shareable message for the Flutter app to preview and share."""
    user_id = None if g.current_user.get("is_admin") else g.current_user["uid"]
    message = get_shareable_message(message_id=message_id, user_id=user_id)
    if not message:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "Shareable message not found.",
                }
            ),
            404,
        )
    return jsonify({"message": message}), 200


@content_bp.post("/<string:message_id>/notify")
@require_auth_or_internal_key
def trigger_message_notification(message_id: str):
    """Send or re-send an FCM notification reminding the user to share the message in Flutter."""
    is_privileged = bool(
        g.current_user.get("is_admin") or g.current_user.get("is_internal")
    )
    user_id = None if is_privileged else g.current_user.get("uid")
    message = get_shareable_message(message_id=message_id, user_id=user_id)
    if not message:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "Shareable message not found.",
                }
            ),
            404,
        )

    notification_result = notify_user_message_ready(message)
    return (
        jsonify(
            {
                "message_id": message_id,
                "notification": notification_result,
            }
        ),
        200,
    )


@content_bp.post("/<string:message_id>/mark-shared")
@require_auth
def mark_message_shared(message_id: str):
    """Called by the client app after the user confirms KakaoTalk sharing completion."""
    user_id = g.current_user["uid"]
    payload = request.get_json(silent=True) or {}
    share_channel = str(payload.get("share_channel") or "kakaotalk_flutter_sdk").strip()

    updated = record_user_share_event(
        message_id=message_id, user_id=user_id, share_channel=share_channel
    )
    if not updated:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "Shareable message not found.",
                }
            ),
            404,
        )

    return jsonify({"message": updated}), 200


@content_bp.post("/<string:message_id>/share-attempt")
@require_auth
def record_share_attempt_endpoint(message_id: str):
    """Record a user-initiated share attempt without claiming delivery or altering message status.

    Critical architectural boundary:
    Clicking 'Share to KakaoTalk' in the PWA notifies the backend that a share was initiated,
    allowing observability into user sharing activity without falsely claiming delivery.
    """
    user_id = g.current_user["uid"]
    payload = request.get_json(silent=True) or {}
    channel = str(payload.get("channel") or "kakao_sdk").strip()

    updated = record_user_share_attempt(
        message_id=message_id, user_id=user_id, channel=channel
    )
    if not updated:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "Shareable message not found.",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "message_id": message_id,
                "recorded": True,
                "channel": channel,
                "share_attempt_count": updated.get("share_attempt_count", 1),
                "last_share_attempt_at": updated.get("last_share_attempt_at"),
                "status": updated.get("status"),
                "kakao_shared": bool(updated.get("kakao_shared", False)),
                "message": updated,
            }
        ),
        200,
    )


@content_bp.post('/imports')
@require_auth
def import_fetched_message():
    """Persist fetched content for the current user; retries preserve existing share state."""
    import hashlib
    from datetime import datetime, timezone
    from urllib.parse import urlsplit
    from google.api_core.exceptions import AlreadyExists
    from flask import current_app
    from app.extensions import get_firestore_client

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'validation_error'}), 400
    fields = {}
    for key, maximum in (('title', 1000), ('body', 400000), ('target_url', 4000), ('source_name', 200), ('endpoint_id', 200)):
        value = payload.get(key, '')
        if not isinstance(value, str) or len(value) > maximum:
            return jsonify({'error': 'validation_error', 'message': f'Invalid {key}'}), 400
        fields[key] = value.strip()
    url = urlsplit(fields['target_url'])
    if not fields['title'] or not fields['body'] or url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
        return jsonify({'error': 'validation_error', 'message': 'Title, body and valid URL required'}), 400
    uid = g.current_user['uid']
    message_id = 'import_' + hashlib.sha256((uid + '\n' + fields['target_url']).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    record = {**fields, 'id': message_id, 'user_id': uid, 'source_id': fields['endpoint_id'],
              'status': 'pending', 'fetch_status': 'success', 'kakao_shared': False,
              'created_at': now, 'updated_at': now, 'formatted_text': fields['body'],
              'items': [{'title': fields['title'], 'url': fields['target_url'], 'source_name': fields['source_name']}]}
    ref = get_firestore_client().collection(current_app.config['FIRESTORE_COLLECTION_MESSAGES']).document(message_id)
    try:
        ref.create(record)
    except AlreadyExists:
        record = ref.get().to_dict()
    return jsonify({'message': record}), 200
