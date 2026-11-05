"""Authentication and authorization helpers using Firebase Authentication."""

from __future__ import annotations

from functools import wraps
import hmac
import logging
from typing import Any, Callable

from firebase_admin import auth as firebase_auth
from flask import current_app, g, jsonify, request

logger = logging.getLogger(__name__)


def _extract_bearer_token() -> str | None:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return decoded claims."""
    return firebase_auth.verify_id_token(id_token, check_revoked=False)


def require_auth(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator requiring a valid Firebase Authentication Bearer ID token.

    Populates `flask.g.current_user` with decoded Firebase token claims
    (including `uid` and optional `email`).
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = _extract_bearer_token()
        if not token:
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Missing or malformed Authorization Bearer token.",
                    }
                ),
                401,
            )

        try:
            decoded_claims = verify_firebase_token(token)
            g.current_user = {
                "uid": decoded_claims.get("uid") or decoded_claims.get("sub"),
                "email": decoded_claims.get("email"),
                "claims": decoded_claims,
            }
        except Exception as exc:
            logger.warning("Firebase ID token verification failed: %s", exc)
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Invalid or expired Firebase ID token.",
                    }
                ),
                401,
            )

        return fn(*args, **kwargs)

    return wrapper


def require_auth_or_internal_key(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Allow either a valid Firebase ID token OR a configured X-Internal-Api-Key.

    Useful for content collection endpoints that can be called either by an
    authenticated user from the Flutter app or by a scheduled ingestion job.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        internal_key_header = request.headers.get("X-Internal-Api-Key")
        expected_key = current_app.config.get("INTERNAL_INGEST_API_KEY")

        if internal_key_header and expected_key:
            if hmac.compare_digest(internal_key_header, expected_key):
                g.current_user = {"uid": "system", "is_internal": True}
                return fn(*args, **kwargs)
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Invalid internal API key.",
                    }
                ),
                401,
            )

        return require_auth(fn)(*args, **kwargs)

    return wrapper
