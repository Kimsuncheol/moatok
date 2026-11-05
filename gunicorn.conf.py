"""Gunicorn configuration for Google Cloud Run deployment.

Respects the `PORT` environment variable injected by Cloud Run (defaulting to 8080)
and configures threaded workers suitable for I/O-bound Firestore, OIDC, RSS, and FCM calls.
"""

from __future__ import annotations

import os


def resolve_bind_address(env: dict[str, str] | None = None) -> str:
    """Resolve the Gunicorn bind address from the PORT environment variable."""
    source = env if env is not None else os.environ
    raw_port = str(source.get("PORT") or "8080").strip()
    try:
        port_num = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"Invalid PORT environment variable: {raw_port!r}") from exc

    if not (1 <= port_num <= 65535):
        raise ValueError(f"PORT must be between 1 and 65535, got {port_num}")

    return f"0.0.0.0:{port_num}"


bind = resolve_bind_address()
worker_class = "gthread"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
capture_output = True
