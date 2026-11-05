"""Endpoints for registering and updating Flutter client device FCM tokens."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_auth
from app.models import ValidationError
from app.repositories.devices_repo import UserDeviceRepository
from app.services.notification_service import register_user_fcm_token

devices_bp = Blueprint("devices", __name__, url_prefix="/api/v1/devices")


@devices_bp.route("/fcm-token", methods=["POST", "PUT", "PATCH"])
@devices_bp.route("", methods=["POST", "PUT", "PATCH"])
@require_auth
def register_token():
    """Register or update the authenticated user's FCM device token from the Flutter app."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Request body must be a JSON object.",
                }
            ),
            400,
        )

    user_id = g.current_user["uid"]
    fcm_token = payload.get("fcm_token") or payload.get("token") or ""
    platform = payload.get("platform") or "flutter"
    device_id = payload.get("device_id")

    try:
        result = register_user_fcm_token(
            user_id=user_id,
            fcm_token=fcm_token,
            platform=platform,
            device_id=device_id,
        )
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400

    return jsonify({"status": "registered", "device": result}), 200


@devices_bp.get("")
@require_auth
def list_my_devices():
    """List registered devices for the authenticated user."""
    user_id = g.current_user["uid"]
    repo = UserDeviceRepository()
    devices = repo.list_devices(user_id=user_id)
    serialized = [
        {
            "device_id": d["device_id"],
            "user_id": d["user_id"],
            "platform": d["platform"],
            "enabled": d["enabled"],
            "updated_at": (
                d["updated_at"].isoformat()
                if hasattr(d.get("updated_at"), "isoformat")
                else d.get("updated_at")
            ),
        }
        for d in devices
    ]
    return jsonify({"devices": serialized, "count": len(serialized)}), 200
