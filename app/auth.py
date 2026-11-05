"""Authentication and authorization helpers using Firebase Authentication."""

from __future__ import annotations

from functools import wraps
import hmac
import logging
from typing import Any, Callable

from firebase_admin import auth as firebase_auth
from flask import current_app, g, has_app_context, jsonify, request

logger = logging.getLogger(__name__)


def _auth_error(
    *,
    error: str,
    code: str,
    message: str,
    status_code: int,
):
    """Build a consistent JSON error response for authentication/authorization failures."""
    return (
        jsonify(
            {
                "error": error,
                "code": code,
                "message": message,
            }
        ),
        status_code,
    )


def _extract_bearer_token() -> tuple[str | None, str | None, str | None]:
    """Extract Bearer token from the Authorization header.

    Returns:
        Tuple of (token, error_code, error_message).
        If extraction succeeds, `token` is non-empty and error fields are None.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.strip():
        return None, "missing_token", "Missing Authorization Bearer token."

    parts = auth_header.strip().split(" ", 1)
    scheme = parts[0].lower()
    if scheme != "bearer":
        return (
            None,
            "invalid_token",
            "Malformed Authorization header. Expected 'Bearer <token>'.",
        )

    if len(parts) < 2 or not parts[1].strip():
        return None, "missing_token", "Missing Authorization Bearer token."

    token = parts[1].strip()
    if any(ch.isspace() for ch in token):
        return (
            None,
            "invalid_token",
            "Malformed Authorization header. Expected 'Bearer <token>'.",
        )

    return token, None, None


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return decoded claims."""
    check_revoked = False
    if has_app_context():
        check_revoked = bool(current_app.config.get("FIREBASE_CHECK_REVOKED", False))
    return firebase_auth.verify_id_token(id_token, check_revoked=check_revoked)


def has_admin_claim(decoded_claims: dict[str, Any]) -> bool:
    """Return True only if verified Firebase custom claims grant administrator privileges.

    Strictly inspects server-verified token claims (`admin is True`,
    `role == 'admin'`, or `'admin' in roles`). Client-supplied headers,
    query parameters, or request body fields are never trusted.
    """
    if not isinstance(decoded_claims, dict):
        return False
    if decoded_claims.get("admin") is True:
        return True
    if decoded_claims.get("role") == "admin":
        return True
    roles = decoded_claims.get("roles")
    if isinstance(roles, (list, tuple, set)) and "admin" in roles:
        return True
    return False


def set_admin_claim(uid: str, is_admin: bool = True) -> dict[str, Any]:
    """Assign or revoke the Firebase 'admin' custom claim for a user via Firebase Admin SDK.

    Must only be called from trusted server-side contexts (e.g., an admin CLI script
    or an endpoint protected by `@require_admin`).
    """
    cleaned_uid = (uid or "").strip()
    if not cleaned_uid:
        raise ValueError("A non-empty user 'uid' is required to set custom claims.")
    if not isinstance(is_admin, bool):
        raise ValueError("'is_admin' must be a boolean.")

    custom_claims = {"admin": is_admin}
    firebase_auth.set_custom_user_claims(cleaned_uid, custom_claims)
    return {"uid": cleaned_uid, "custom_claims": custom_claims}


def require_auth(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator requiring a valid Firebase Authentication Bearer ID token.

    Populates `flask.g.current_user` exclusively from verified Firebase ID token
    claims (`uid`, `email`, `role`, `is_admin`, `claims`).
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token, err_code, err_msg = _extract_bearer_token()
        if not token:
            return _auth_error(
                error="unauthorized",
                code=err_code or "missing_token",
                message=err_msg or "Missing Authorization Bearer token.",
                status_code=401,
            )

        try:
            decoded_claims = verify_firebase_token(token)
        except firebase_auth.ExpiredIdTokenError as exc:
            logger.warning("Expired Firebase ID token: %s", exc)
            return _auth_error(
                error="unauthorized",
                code="token_expired",
                message="Firebase ID token has expired.",
                status_code=401,
            )
        except firebase_auth.RevokedIdTokenError as exc:
            logger.warning("Revoked Firebase ID token: %s", exc)
            return _auth_error(
                error="unauthorized",
                code="token_revoked",
                message="Firebase ID token has been revoked.",
                status_code=401,
            )
        except firebase_auth.UserDisabledError as exc:
            logger.warning("Disabled Firebase user: %s", exc)
            return _auth_error(
                error="unauthorized",
                code="user_disabled",
                message="User account has been disabled.",
                status_code=401,
            )
        except (firebase_auth.InvalidIdTokenError, ValueError) as exc:
            logger.warning("Invalid Firebase ID token: %s", exc)
            return _auth_error(
                error="unauthorized",
                code="invalid_token",
                message="Invalid Firebase ID token.",
                status_code=401,
            )
        except Exception as exc:
            logger.warning("Firebase ID token verification failed: %s", exc)
            return _auth_error(
                error="unauthorized",
                code="invalid_token",
                message="Invalid Firebase ID token.",
                status_code=401,
            )

        if not isinstance(decoded_claims, dict):
            return _auth_error(
                error="unauthorized",
                code="invalid_token",
                message="Invalid Firebase ID token.",
                status_code=401,
            )

        uid = str(decoded_claims.get("uid") or decoded_claims.get("sub") or "").strip()
        if not uid:
            return _auth_error(
                error="unauthorized",
                code="invalid_token",
                message="Invalid Firebase ID token: missing user identifier.",
                status_code=401,
            )

        is_admin = has_admin_claim(decoded_claims)
        g.current_user = {
            "uid": uid,
            "email": decoded_claims.get("email"),
            "role": "admin" if is_admin else "user",
            "is_admin": is_admin,
            "is_internal": False,
            "claims": decoded_claims,
        }

        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator requiring a verified Firebase ID token with administrator custom claims.

    Never trusts roles supplied by the client in request headers, query params, or JSON body.
    """

    @wraps(fn)
    @require_auth
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        current_user = getattr(g, "current_user", None) or {}
        if current_user.get("is_admin") is not True:
            return _auth_error(
                error="forbidden",
                code="admin_required",
                message="Administrator privileges required.",
                status_code=403,
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

        if internal_key_header is not None:
            if expected_key and hmac.compare_digest(internal_key_header, expected_key):
                g.current_user = {
                    "uid": "system",
                    "email": None,
                    "role": "system",
                    "is_admin": False,
                    "is_internal": True,
                    "claims": {},
                }
                return fn(*args, **kwargs)
            return _auth_error(
                error="unauthorized",
                code="invalid_internal_key",
                message="Invalid internal API key.",
                status_code=401,
            )

        return require_auth(fn)(*args, **kwargs)

    return wrapper
