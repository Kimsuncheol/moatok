"""Endpoints for registering Flutter client device FCM tokens."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_auth
from app.models import ValidationError
from app.services.notification_service import register_user_fcm_token

devices_bp = Blueprint("devices", __name__, url_prefix="/api/v1/devices")


@devices_bp.post("/fcm-token")
@require_auth
def register_token():
    """Register or update the authenticated user's FCM token from the Flutter app."""
    payload = request.get_json(silent=True) or {}
    user_id = g.current_user["uid"]

    try:
        result = register_user_fcm_token(
            user_id=user_id,
            fcm_token=payload.get("fcm_token", ""),
            platform=payload.get("platform", "flutter"),
        )
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    return jsonify({"status": "registered", "device": result}), 200
