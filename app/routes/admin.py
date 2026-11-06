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


@admin_bp.get("/integrations/english-scrapper")
@require_admin
def english_scrapper_status():
    from app.extensions import get_firestore_client
    from flask import current_app
    doc = get_firestore_client().collection('integration_status').document('english_scrapper').get()
    return jsonify(enabled=current_app.config['ENGLISH_SCRAPER_ENABLED'],
                   url=current_app.config['ENGLISH_SCRAPER_URL'], last_sync=doc.to_dict() if doc.exists else None)


@admin_bp.post("/integrations/english-scrapper/sync")
@require_admin
def english_scrapper_sync():
    from app.services.english_scraper import sync_english_lessons
    payload = request.get_json(silent=True) or {}
    offset = payload.get('offset', 0) if isinstance(payload, dict) else None
    if type(offset) is not int or offset < 0:
        return jsonify(error='validation_error', message='offset must be a nonnegative integer'), 400
    try:
        return jsonify(sync_english_lessons(offset=offset))
    except Exception:
        from flask import current_app
        current_app.logger.exception('English scraper sync unavailable')
        return jsonify(error='upstream_unavailable', message='English lesson sync failed. Retry shortly.'), 502


@share_messages_bp.get("/<string:message_id>/english-lesson")
@require_auth
def english_lesson_detail(message_id):
    from app.extensions import get_firestore_client
    message = ShareMessageRepository().get(message_id)
    if not message:
        return jsonify(error='not_found'), 404
    doc = get_firestore_client().collection('english_lessons').document(message['article_id']).get()
    if not doc.exists:
        return jsonify(error='not_found'), 404
    return jsonify(lesson=doc.to_dict())


@admin_bp.get('/integrations/english-scrapper/lessons')
@require_admin
def english_scrapper_review_lessons():
    """Inspect recent imports, including held lessons and missing sections."""
    from app.extensions import get_firestore_client
    docs = get_firestore_client().collection('english_lessons').limit(100).stream()
    return jsonify(lessons=[doc.to_dict() for doc in docs])


@share_messages_bp.post('/english-lessons/fetch')
@admin_bp.post('/integrations/english-scrapper/fetch')
def english_scrapper_fetch():
    from app.extensions import get_firestore_client
    from app.services.english_scraper import EnglishScraperClient, import_saved_lesson, validate_english_article_url
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error='validation_error', message='A JSON object is required.'), 400
    try:
        url = validate_english_article_url(payload.get('url'))
        for key, limit in [('title', 100), ('note', 160)]:
            if not isinstance(payload.get(key, ''), str) or len(payload.get(key, '')) > limit:
                raise ValidationError(f'{key} must be text of at most {limit} characters.')
    except (ValidationError, ValueError) as exc:
        return jsonify(error='validation_error', message=str(exc)), 400
    try:
        saved = EnglishScraperClient().scrape_article(url)
        result = import_saved_lesson(saved, db=get_firestore_client(), notify=False,
            title=payload.get('title', '').strip(), note=payload.get('note', '').strip())
        return jsonify(result)
    except Exception:
        from flask import current_app
        current_app.logger.exception('English URL fetch failed')
        return jsonify(error='fetch_failed', message='Could not extract this lesson. Check the article URL and retry.'), 502
