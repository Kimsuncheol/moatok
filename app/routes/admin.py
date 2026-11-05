"""Endpoints for authenticated user session inspection and administrator operations."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_admin, require_auth, set_admin_claim
from app.models import ValidationError
from app.repositories.share_messages_repo import ShareMessageRepository
from app.services.content_service import list_shareable_messages
from app.services.notification_service import notify_pending_share_message
from app.services.share_message_generator import edit_pending_share_message

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
share_messages_bp = Blueprint(
    "share_messages", __name__, url_prefix="/api/v1/share-messages"
)


@auth_bp.get("/me")
@require_auth
def get_current_user_profile():
    """Return the verified Firebase identity and role for the authenticated caller.

    Roles are derived strictly from verified Firebase ID token custom claims,
    never from client-supplied headers, query parameters, or request bodies.
    """
    return (
        jsonify(
            {
                "user": {
                    "uid": g.current_user["uid"],
                    "email": g.current_user.get("email"),
                    "role": g.current_user["role"],
                    "is_admin": g.current_user["is_admin"],
                }
            }
        ),
        200,
    )


@admin_bp.get("/messages")
@require_admin
def admin_list_all_messages():
    """List prepared shareable messages across all users (administrator only)."""
    user_id = (request.args.get("user_id") or "").strip() or None
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", "50"))
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


@admin_bp.post("/users/<string:target_uid>/claims")
@require_admin
def admin_update_user_claims(target_uid: str):
    """Assign or revoke the Firebase 'admin' custom claim for a target user (administrator only)."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("admin"), bool):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Request body must be JSON containing a boolean 'admin' field.",
                }
            ),
            400,
        )

    try:
        result = set_admin_claim(uid=target_uid, is_admin=payload["admin"])
    except ValueError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    return (
        jsonify(
            {
                "status": "updated",
                "uid": result["uid"],
                "custom_claims": result["custom_claims"],
            }
        ),
        200,
    )


def _handle_list_share_messages():
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "invalid_query_param",
                    "message": "Query parameter 'limit' must be an integer.",
                }
            ),
            400,
        )

    repo = ShareMessageRepository()
    try:
        records = repo.list_messages(status=status, limit=limit)
    except ValidationError as exc:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "invalid_status",
                    "message": str(exc),
                }
            ),
            400,
        )

    serialized = [ShareMessageRepository.to_api_dict(r) for r in records]
    return jsonify({"share_messages": serialized, "count": len(serialized)}), 200


def _handle_get_share_message(message_id: str):
    repo = ShareMessageRepository()
    record = repo.get(message_id)
    if not record:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "code": "share_message_not_found",
                    "message": f"Share message '{message_id}' not found.",
                }
            ),
            404,
        )
    return jsonify({"share_message": ShareMessageRepository.to_api_dict(record)}), 200


def _handle_edit_pending_share_message(message_id: str):
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "invalid_json",
                    "message": "Request body must be a valid JSON object.",
                }
            ),
            400,
        )

    try:
        updated = edit_pending_share_message(message_id, payload)
    except ValidationError as exc:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "validation_error",
                    "message": str(exc),
                }
            ),
            400,
        )

    if not updated:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "code": "share_message_not_found",
                    "message": f"Share message '{message_id}' not found.",
                }
            ),
            404,
        )

    return jsonify({"share_message": updated}), 200


def _handle_notify_share_message(message_id: str):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "invalid_json",
                    "message": "Request body must be a valid JSON object.",
                }
            ),
            400,
        )

    repo = ShareMessageRepository()
    record = repo.get(message_id)
    if not record:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "code": "share_message_not_found",
                    "message": f"Share message '{message_id}' not found.",
                }
            ),
            404,
        )

    user_id = payload.get("user_id")
    user_ids = payload.get("user_ids")
    notification_result = notify_pending_share_message(
        record,
        user_id=user_id,
        target_user_ids=user_ids if isinstance(user_ids, list) else None,
        share_repo=repo,
    )
    refreshed = repo.get(message_id)
    return (
        jsonify(
            {
                "share_message": (
                    ShareMessageRepository.to_api_dict(refreshed)
                    if refreshed
                    else ShareMessageRepository.to_api_dict(record)
                ),
                "notification": notification_result,
            }
        ),
        200,
    )


admin_bp.add_url_rule(
    "/share-messages",
    endpoint="list_share_messages",
    view_func=require_admin(_handle_list_share_messages),
    methods=["GET"],
)
admin_bp.add_url_rule(
    "/share-messages/<string:message_id>",
    endpoint="get_share_message",
    view_func=require_admin(_handle_get_share_message),
    methods=["GET"],
)
admin_bp.add_url_rule(
    "/share-messages/<string:message_id>",
    endpoint="edit_share_message",
    view_func=require_admin(_handle_edit_pending_share_message),
    methods=["PUT", "PATCH"],
)
admin_bp.add_url_rule(
    "/share-messages/<string:message_id>/notify",
    endpoint="notify_share_message",
    view_func=require_admin(_handle_notify_share_message),
    methods=["POST"],
)
admin_bp.add_url_rule(
    "/messages/<string:message_id>",
    endpoint="edit_admin_message_alias",
    view_func=require_admin(_handle_edit_pending_share_message),
    methods=["PUT", "PATCH"],
)

share_messages_bp.add_url_rule(
    "",
    endpoint="list_share_messages",
    view_func=require_admin(_handle_list_share_messages),
    methods=["GET"],
)
share_messages_bp.add_url_rule(
    "/<string:message_id>",
    endpoint="get_share_message",
    view_func=require_admin(_handle_get_share_message),
    methods=["GET"],
)
share_messages_bp.add_url_rule(
    "/<string:message_id>",
    endpoint="edit_share_message",
    view_func=require_admin(_handle_edit_pending_share_message),
    methods=["PUT", "PATCH"],
)
share_messages_bp.add_url_rule(
    "/<string:message_id>/notify",
    endpoint="notify_share_message",
    view_func=require_admin(_handle_notify_share_message),
    methods=["POST"],
)
