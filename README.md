# Moatok Backend (Content Collection & KakaoTalk Sharing Assistant)

A production-oriented Python **Flask** backend that collects and formats content, stores shareable message drafts in **Cloud Firestore**, authenticates users via **Firebase Authentication**, and sends push notifications via **Firebase Cloud Messaging (FCM)** so users can review and share messages from a companion **Flutter** application.

## Architectural Boundary & KakaoTalk Sharing Model

> **Important**: This backend **does not** automatically post messages to KakaoTalk Open Chat rooms or personal chats on a user's behalf.
>
> Instead, it follows a **user-initiated sharing workflow**:
> 1. **Collect & Prepare**: The backend ingests content items and formats them into both plain text (`formatted_text`) and a structured template payload (`kakao_share_payload`) tailored for the Flutter client.
> 2. **Store**: Prepared messages are persisted in **Cloud Firestore** (`shareable_messages` collection) with `sharing_mode: "user_initiated_flutter"`.
> 3. **Notify**: The backend sends a push notification via **Firebase Cloud Messaging (FCM)** to the user's registered Flutter device(s).
> 4. **User-Initiated Share in Flutter**: When the user taps the notification or opens the Flutter app, the Flutter app fetches the prepared message from this backend and invokes the KakaoTalk Flutter SDK (or system share sheet) upon explicit user action, then calls `POST /api/v1/messages/<id>/mark-shared` to record completion.

---

## Project Structure

```text
.
├── app/
│   ├── __init__.py                 # Flask application factory, logging, CORS, error handlers
│   ├── auth.py                     # Firebase Auth ID token verification & internal API key guard
│   ├── config.py                   # Environment-based configuration (dev, testing, prod)
│   ├── extensions.py               # Firebase Admin & Firestore initialization via ADC
│   ├── models.py                   # Data models & payload validation
│   ├── routes/
│   │   ├── health.py               # GET /health endpoint
│   │   ├── devices.py              # POST /api/v1/devices/fcm-token
│   │   └── content.py              # /api/v1/messages endpoints
│   └── services/
│       ├── content_service.py      # Content formatting & Firestore persistence
│       └── notification_service.py # FCM token registration & push notification dispatch
├── tests/
│   ├── conftest.py                 # Pytest fixtures & in-memory Firestore/Firebase mocks
│   ├── test_health.py              # Health endpoint tests
│   └── test_content_and_notifications.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── wsgi.py                         # WSGI entrypoint for Gunicorn
```

---

## Security & Credentials

- **Never commit secrets or service account JSON files**: `.gitignore` and `.dockerignore` exclude `.env` files and `*service-account*.json` / `*credentials*.json`.
- **Deployed Environments (Cloud Run, GKE, App Engine)**: Leave `GOOGLE_APPLICATION_CREDENTIALS` unset. The backend initializes `firebase_admin` with `credentials.ApplicationDefault()`, which automatically uses the runtime's attached Google Cloud service account.
- **Local Development**: Authenticate with Google Cloud Application Default Credentials:
  ```bash
  gcloud auth application-default login
  ```

---

## Local Setup Instructions

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your Google Cloud / Firebase project details:

```bash
cp .env.example .env
```

Authenticate locally with Application Default Credentials:

```bash
gcloud auth application-default login
```

### 3. Run the development server

```bash
.venv/bin/python wsgi.py
```

Verify the health endpoint:

```bash
curl http://localhost:8080/health
```

### 4. Run automated tests

Tests run completely offline in `testing` mode using mocked Firebase Auth, FCM, and an in-memory Firestore test double:

```bash
.venv/bin/pytest -v
```

---

## Docker Build & Run

```bash
docker build -t moatok-backend .
docker run --rm -p 8080:8080 --env-file .env moatok-backend
```

---

## API Overview

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Health check for load balancers & orchestrators |
| `POST` | `/api/v1/devices/fcm-token` | Firebase Bearer Token | Register a Flutter device's FCM token for push notifications |
| `POST` | `/api/v1/messages` | Firebase Bearer Token or `X-Internal-Api-Key` | Collect content items, store a shareable message in Firestore, and optionally notify the user via FCM |
| `GET` | `/api/v1/messages` | Firebase Bearer Token | List prepared shareable messages for the authenticated user |
| `GET` | `/api/v1/messages/<id>` | Firebase Bearer Token | Retrieve a single prepared message payload for the Flutter share preview |
| `POST` | `/api/v1/messages/<id>/notify` | Firebase Bearer Token or `X-Internal-Api-Key` | Send or re-send an FCM push notification for a prepared message |
| `POST` | `/api/v1/messages/<id>/mark-shared` | Firebase Bearer Token | Mark a message as shared after the user completes KakaoTalk sharing in Flutter |
