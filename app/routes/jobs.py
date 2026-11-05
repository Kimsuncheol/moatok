"""Protected internal endpoint for Cloud Scheduler content collection jobs."""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.auth import require_scheduler_auth
from app.services.rss_collector import collect_rss_articles

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.post("/internal/jobs/collect")
@require_scheduler_auth
def run_scheduled_collection_job():
    """Execute the scheduled content collection job triggered by Cloud Scheduler.

    1. Verifies the caller's Google OIDC ID token and authorizes the configured
       Cloud Scheduler service account (`@require_scheduler_auth`).
    2. Collects enabled content sources.
    3. Saves new articles and pending share messages idempotently using
       deterministic document IDs and Firestore transactions.
    4. Dispatches concise FCM notifications to registered users for newly
       generated pending share messages (once per share message).
    5. Returns a structured job summary.
    """
    summary = collect_rss_articles(notify_users=True)
    scheduler_email = (getattr(g, "current_scheduler", None) or {}).get("email")

    return (
        jsonify(
            {
                "status": "completed",
                "scheduler_service_account": scheduler_email,
                "summary": summary,
                **summary,
            }
        ),
        200,
    )
