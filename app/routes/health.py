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


@health_bp.get("/api/v1/integrations/chosun-daily/articles")
def chosun_daily_articles():
    """Read the latest ten public articles through a fixed, bounded upstream request."""
    import json
    from app.services.url_validator import fetch_and_validate_source_url
    from app.models import ValidationError

    try:
        probe = fetch_and_validate_source_url(
            "https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10",
            allowed_domains=("chosun-daily-api-tv70.onrender.com",),
            timeout_seconds=75, max_bytes=2 * 1024 * 1024, max_redirects=0,
        )
        if probe.status_code != 200:
            raise ValueError("Upstream unavailable")
        data = json.loads(probe.content)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Invalid article page")
        return jsonify({"items": data["items"][:10]})
    except (ValidationError, ValueError, OSError):
        return jsonify({"error": "Chosun Daily is temporarily unavailable"}), 502
