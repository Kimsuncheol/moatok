"""Administrator-only REST endpoints to create, list, update, enable, and disable content sources."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.auth import require_admin
from app.models import ValidationError
from app.services.rss_collector import collect_rss_articles
from app.services.source_service import (
    create_source_entry,
    get_source_entry,
    get_supported_source_types,
    list_source_entries,
    set_source_enabled_state,
    update_source_entry,
)
from app.services.url_validator import UrlValidationError

admin_sources_bp = Blueprint("admin_sources", __name__, url_prefix="/api/v1/admin/sources")
sources_bp = Blueprint("sources", __name__, url_prefix="/api/v1/sources")


def _validation_error_response(exc: ValidationError, status_code: int = 400):
    code = getattr(exc, "code", "validation_error")
    return (
        jsonify(
            {
                "error": "validation_error",
                "code": code,
                "message": str(exc),
            }
        ),
        status_code,
    )


def _not_found_response(source_id: str):
    return (
        jsonify(
            {
                "error": "not_found",
                "code": "source_not_found",
                "message": f"Content source '{source_id}' not found.",
            }
        ),
        404,
    )


def _handle_create_source():
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
        source_dict, created = create_source_entry(payload)
    except (UrlValidationError, ValidationError) as exc:
        return _validation_error_response(exc, status_code=400)

    return (
        jsonify(
            {
                "source": source_dict,
                "created": created,
            }
        ),
        201 if created else 200,
    )


def _handle_list_sources():
    enabled_only_param = (
        request.args.get("enabled_only") or request.args.get("enabled") or ""
    ).strip().lower()
    if enabled_only_param in {"true", "1", "yes"}:
        enabled_only = True
    elif enabled_only_param in {"", "false", "0", "no"}:
        enabled_only = False
    else:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "code": "invalid_query_param",
                    "message": "Query parameter 'enabled_only' must be a boolean ('true' or 'false').",
                }
            ),
            400,
        )

    source_type = request.args.get("source_type")
    try:
        limit = int(request.args.get("limit", "100"))
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

    try:
        sources = list_source_entries(
            enabled_only=enabled_only,
            source_type=source_type,
            limit=limit,
        )
    except ValidationError as exc:
        return _validation_error_response(exc, status_code=400)

    return (
        jsonify(
            {
                "sources": sources,
                "count": len(sources),
                "supported_source_types": get_supported_source_types(),
            }
        ),
        200,
    )


def _handle_get_source(source_id: str):
    source = get_source_entry(source_id)
    if not source:
        return _not_found_response(source_id)
    return jsonify({"source": source}), 200


def _handle_update_source(source_id: str):
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
        updated = update_source_entry(source_id, payload)
    except (UrlValidationError, ValidationError) as exc:
        return _validation_error_response(exc, status_code=400)

    if not updated:
        return _not_found_response(source_id)

    return jsonify({"source": updated}), 200


def _handle_enable_source(source_id: str):
    updated = set_source_enabled_state(source_id, enabled=True)
    if not updated:
        return _not_found_response(source_id)
    return jsonify({"source": updated}), 200


def _handle_disable_source(source_id: str):
    updated = set_source_enabled_state(source_id, enabled=False)
    if not updated:
        return _not_found_response(source_id)
    return jsonify({"source": updated}), 200


def _handle_collect_sources():
    summary = collect_rss_articles()
    return jsonify({"summary": summary}), 200


for _bp in (admin_sources_bp, sources_bp):
    _bp.add_url_rule(
        "/collect",
        endpoint="collect_sources",
        view_func=require_admin(_handle_collect_sources),
        methods=["POST"],
    )
    _bp.add_url_rule(
        "",
        endpoint="create_source",
        view_func=require_admin(_handle_create_source),
        methods=["POST"],
    )
    _bp.add_url_rule(
        "",
        endpoint="list_sources",
        view_func=require_admin(_handle_list_sources),
        methods=["GET"],
    )
    _bp.add_url_rule(
        "/<string:source_id>",
        endpoint="get_source",
        view_func=require_admin(_handle_get_source),
        methods=["GET"],
    )
    _bp.add_url_rule(
        "/<string:source_id>",
        endpoint="update_source",
        view_func=require_admin(_handle_update_source),
        methods=["PUT", "PATCH"],
    )
    _bp.add_url_rule(
        "/<string:source_id>/enable",
        endpoint="enable_source",
        view_func=require_admin(_handle_enable_source),
        methods=["POST", "PATCH"],
    )
    _bp.add_url_rule(
        "/<string:source_id>/disable",
        endpoint="disable_source",
        view_func=require_admin(_handle_disable_source),
        methods=["POST", "PATCH"],
    )
