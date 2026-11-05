"""Firebase Admin SDK and Cloud Firestore client initialization.

Uses Application Default Credentials (ADC) by default so deployed environments
(such as Cloud Run or GKE) authenticate via their attached service account
without storing or committing secret key files.
"""

from __future__ import annotations

import logging
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask

logger = logging.getLogger(__name__)

_firestore_client: Any = None


def init_firebase(app: Flask) -> None:
    """Initialize Firebase Admin SDK using Application Default Credentials."""
    if app.config.get("TESTING"):
        logger.debug("Skipping live Firebase initialization in TESTING mode.")
        return

    if not firebase_admin._apps:
        options: dict[str, Any] = {}
        project_id = app.config.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            options["projectId"] = project_id

        # credentials.ApplicationDefault() automatically uses:
        # 1. GOOGLE_APPLICATION_CREDENTIALS env var if set for local dev, or
        # 2. gcloud ADC credentials locally, or
        # 3. Attached service account metadata server in Cloud Run / GCP environments.
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, options=options or None)
        logger.info(
            "Initialized Firebase Admin SDK with Application Default Credentials (project=%s).",
            project_id or "auto-detected",
        )


def get_firestore_client() -> Any:
    """Return the Cloud Firestore client instance."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    _firestore_client = firestore.client()
    return _firestore_client


def set_firestore_client(client: Any) -> None:
    """Override the Firestore client (used for dependency injection in tests)."""
    global _firestore_client
    _firestore_client = client
