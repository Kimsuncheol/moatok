"""Integration settings available to signed-in Moatok users."""

from flask import Blueprint, jsonify, request

from app.auth import require_auth
from app.services import english_schedule

integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")


@integrations_bp.route("/english-scrapper/schedule", methods=["GET", "PUT"])
@require_auth
def english_scraper_schedule():
    return handle_english_scraper_schedule()


def handle_english_scraper_schedule():
    """Forward validated schedule settings using server-side credentials."""
    payload = request.get_json(silent=True) if request.method == "PUT" else None
    try:
        return jsonify(english_schedule.cloud_schedule(request.method, payload))
    except english_schedule.ScheduleError as exc:
        code = "scraper_schedule_unavailable" if exc.status >= 500 else "validation_error"
        return jsonify(error=code, message=str(exc)), exc.status
