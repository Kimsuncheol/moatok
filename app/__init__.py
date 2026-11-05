"""Flask application factory for the Moatok backend."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.config import Config, get_config
from app.extensions import init_firebase
from app.routes.admin import admin_bp, auth_bp, share_messages_bp
from app.routes.content import content_bp
from app.routes.devices import devices_bp
from app.routes.health import health_bp
from app.routes.jobs import jobs_bp
from app.routes.sources import admin_sources_bp, sources_bp


def _configure_logging(app: Flask) -> None:
    log_level_name = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        return (
            jsonify(
                {
                    "error": exc.name.lower().replace(" ", "_"),
                    "message": exc.description,
                }
            ),
            exc.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        app.logger.exception("Unhandled exception: %s", exc)
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": "An unexpected internal error occurred.",
                }
            ),
            500,
        )


def _register_cors_and_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_headers(response):
        allowed_origins = app.config.get("CORS_ALLOWED_ORIGINS", "*")
        response.headers["Access-Control-Allow-Origin"] = allowed_origins
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Internal-Api-Key"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app(
    config_name: str | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)

    config_cls: type[Config] = get_config(config_name)
    app.config.from_object(config_cls)
    if config_overrides:
        app.config.update(config_overrides)

    _configure_logging(app)
    init_firebase(app)
    _register_cors_and_security_headers(app)
    _register_error_handlers(app)

    # Register modular Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(share_messages_bp)
    app.register_blueprint(admin_sources_bp)
    app.register_blueprint(sources_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(content_bp)

    return app
