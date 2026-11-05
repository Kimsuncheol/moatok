"""Health check endpoint for load balancers and container orchestrators."""

from __future__ import annotations

from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Return service health and operational metadata."""
    return (
        jsonify(
            {
                "status": "ok",
                "service": "moatok-backend",
                "environment": current_app.config.get("ENV", "production"),
                "sharing_mode": "user_initiated_flutter",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        200,
    )
