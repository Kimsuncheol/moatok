"""Endpoints for authenticated user session inspection and administrator operations."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_admin, require_auth, set_admin_claim
from app.models import ValidationError
from app.services.content_service import list_shareable_messages

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


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
