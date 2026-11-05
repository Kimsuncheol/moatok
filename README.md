# Moatok Backend (Content Collection & KakaoTalk Sharing Assistant)

A production-oriented Python **Flask** backend that collects and formats content, stores shareable message drafts in **Cloud Firestore**, authenticates users via **Firebase Authentication**, enforces administrator access using **verified Firebase custom claims**, and sends push notifications via **Firebase Cloud Messaging (FCM)** so users can review and share messages from a companion **Flutter** application.

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
│   ├── auth.py                     # Firebase ID token verification, custom claim admin guard & internal API key guard
│   ├── config.py                   # Environment-based configuration (dev, testing, prod)
│   ├── extensions.py               # Firebase Admin & Firestore initialization via ADC
│   ├── models.py                   # Data models & payload validation
│   ├── repositories/
│   │   ├── __init__.py             # Repository exports
│   │   ├── firestore_utils.py      # UTC timestamp normalization, deterministic IDs & secret guards
│   │   ├── sources_repo.py         # `sources` collection repository
│   │   ├── articles_repo.py        # `articles` collection repository (transactional deduplication)
│   │   ├── share_messages_repo.py  # `share_messages` collection repository (transactional deduplication)
│   │   └── devices_repo.py         # `users/{userId}/devices` subcollection repository
│   ├── routes/
│   │   ├── health.py               # Public GET /health endpoint
│   │   ├── admin.py                # GET /api/v1/auth/me & /api/v1/admin/* endpoints
│   │   ├── sources.py              # Admin-only /api/v1/admin/sources & /api/v1/sources endpoints
│   │   ├── devices.py              # POST /api/v1/devices/fcm-token
│   │   └── content.py              # /api/v1/messages endpoints
│   └── services/
│       ├── content_service.py           # Content formatting & Firestore persistence
│       ├── notification_service.py      # FCM token registration & push notification dispatch
│       ├── rss_collector.py             # RSS collection service, feed parsing, deduplication & safe logging
│       ├── share_message_generator.py   # Rule-based pending share message generator & length guards
│       ├── source_connectors.py         # RSS and extensible Official API source connectors
│       ├── source_service.py            # Source CRUD orchestration & validation
│       └── url_validator.py             # Domain allowlist, SSRF IP/DNS checks, redirect, timeout & size guards
├── tests/
│   ├── conftest.py                      # Pytest fixtures & in-memory Firestore/Firebase mocks
│   ├── test_auth.py                     # Auth, expired/invalid tokens, admin custom claims & role-spoofing tests
│   ├── test_repositories.py             # Firestore repository, UTC, deduplication & secret-rejection tests
│   ├── test_rss_collector.py            # RSS collection, deduplication, fault tolerance & log redaction tests
│   ├── test_share_message_generator.py  # Rule-based share message generator, length limits & admin edit tests
│   ├── test_sources.py                  # Admin content source endpoints & SSRF/redirect/timeout/size tests
│   ├── test_health.py                   # Public health endpoint tests
│   └── test_content_and_notifications.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── wsgi.py                         # WSGI entrypoint for Gunicorn
```

---

## Authentication & Authorization Architecture

### 1. Firebase ID Token Verification (`@require_auth`)
All protected user-facing endpoints require an HTTP `Authorization: Bearer <FIREBASE_ID_TOKEN>` header.
The backend verifies the token signature, expiration, and claims server-side using `firebase_admin.auth.verify_id_token()`.

### 2. Consistent JSON Authentication & Authorization Errors
Every authentication or authorization failure returns a structured JSON payload containing `error`, `code`, and `message`:

| Scenario | HTTP Status | `error` | `code` | `message` |
| :--- | :--- | :--- | :--- | :--- |
| Missing `Authorization` header or empty Bearer token | `401` | `"unauthorized"` | `"missing_token"` | `"Missing Authorization Bearer token."` |
| Malformed `Authorization` header (e.g. non-Bearer scheme) | `401` | `"unauthorized"` | `"invalid_token"` | `"Malformed Authorization header. Expected 'Bearer <token>'."` |
| Expired Firebase ID token (`ExpiredIdTokenError`) | `401` | `"unauthorized"` | `"token_expired"` | `"Firebase ID token has expired."` |
| Revoked Firebase ID token (`RevokedIdTokenError`) | `401` | `"unauthorized"` | `"token_revoked"` | `"Firebase ID token has been revoked."` |
| Disabled Firebase user (`UserDisabledError`) | `401` | `"unauthorized"` | `"user_disabled"` | `"User account has been disabled."` |
| Invalid/forged Firebase ID token (`InvalidIdTokenError`) | `401` | `"unauthorized"` | `"invalid_token"` | `"Invalid Firebase ID token."` |
| Valid user token lacking verified admin custom claim | `403` | `"forbidden"` | `"admin_required"` | `"Administrator privileges required."` |

### 3. Zero Trust for Client-Supplied Roles
The API **never** accepts roles or privilege flags supplied by the client (such as `role`, `admin`, or `is_admin` in JSON request bodies, query strings, or custom HTTP headers like `X-User-Role`). Authorization decisions rely exclusively on cryptographic Firebase ID token claims verified by the Firebase Admin SDK (`has_admin_claim(decoded_claims)`).

### 4. Assigning an Administrator Custom Claim Securely

Administrator privileges are granted via Firebase Custom User Claims (`{"admin": true}`) using the **Firebase Admin SDK** from a trusted server environment. Custom claims cannot be modified by client SDKs.

#### Step A: Bootstrap the Initial Administrator (Trusted Server / CLI)
Run a one-off command from a secure administrative environment authenticated via Google Cloud Application Default Credentials (`gcloud auth application-default login`) where the caller holds the **Firebase Authentication Admin** (`roles/firebaseauth.admin`) IAM role:

```bash
python3 -c '
import firebase_admin
from firebase_admin import auth, credentials

firebase_admin.initialize_app(credentials.ApplicationDefault())
auth.set_custom_user_claims("TARGET_FIREBASE_UID", {"admin": True})
print("Assigned admin custom claim successfully.")
'
```

#### Step B: Assign or Revoke Admin Claims via the Admin API
Once an administrator exists, they can manage custom claims for other users via the `@require_admin`-protected endpoint (which calls `app.auth.set_admin_claim()` -> `firebase_admin.auth.set_custom_user_claims()`):

```bash
curl -X POST http://localhost:8080/api/v1/admin/users/<TARGET_UID>/claims \
  -H "Authorization: Bearer <ADMIN_FIREBASE_ID_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"admin": true}'
```

#### Step C: Token Propagation on the Client
Firebase custom claims are embedded into the user's signed ID token when minted. After a user's custom claim is updated on the server, the client application (e.g., Flutter) must force an ID token refresh (`await FirebaseAuth.instance.currentUser?.getIdToken(true)`) or re-authenticate so the updated `{"admin": true}` claim is included in subsequent `Authorization: Bearer <ID_TOKEN>` requests.

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

Verify the public health endpoint:

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
| `GET` | `/api/v1/auth/me` | Firebase Bearer Token | Return verified user identity and role from Firebase ID token claims |
| `POST` | `/api/v1/devices/fcm-token` | Firebase Bearer Token | Register a Flutter device's FCM token for push notifications |
| `POST` | `/api/v1/messages` | Firebase Bearer Token or `X-Internal-Api-Key` | Collect content items, store a shareable message in Firestore, and optionally notify the user via FCM |
| `GET` | `/api/v1/messages` | Firebase Bearer Token | List prepared shareable messages for the authenticated user |
| `GET` | `/api/v1/messages/<id>` | Firebase Bearer Token | Retrieve a single prepared message payload for the Flutter share preview |
| `POST` | `/api/v1/messages/<id>/notify` | Firebase Bearer Token or `X-Internal-Api-Key` | Send or re-send an FCM push notification for a prepared message |
| `POST` | `/api/v1/messages/<id>/mark-shared` | Firebase Bearer Token | Mark a message as shared after the user completes KakaoTalk sharing in Flutter |
| `GET` | `/api/v1/admin/messages` | Firebase Admin Claim (`admin: true`) | List prepared shareable messages across all users |
| `POST` | `/api/v1/admin/users/<uid>/claims` | Firebase Admin Claim (`admin: true`) | Assign or revoke the `admin` Firebase custom claim for a target user |
| `POST` | `/api/v1/admin/sources` (`/api/v1/sources`) | Firebase Admin Claim (`admin: true`) | Validate and create an RSS or official API content source |
| `GET` | `/api/v1/admin/sources` (`/api/v1/sources`) | Firebase Admin Claim (`admin: true`) | List content sources (supports `enabled_only`, `source_type`, `limit`) |
| `GET` | `/api/v1/admin/sources/<id>` (`/api/v1/sources/<id>`) | Firebase Admin Claim (`admin: true`) | Retrieve a single content source by ID |
| `PATCH` / `PUT` | `/api/v1/admin/sources/<id>` (`/api/v1/sources/<id>`) | Firebase Admin Claim (`admin: true`) | Update a content source's `name`, `url`, `source_type`, or `enabled` state |
| `POST` | `/api/v1/admin/sources/<id>/enable` (`/api/v1/sources/<id>/enable`) | Firebase Admin Claim (`admin: true`) | Enable a content source |
| `POST` | `/api/v1/admin/sources/<id>/disable` (`/api/v1/sources/<id>/disable`) | Firebase Admin Claim (`admin: true`) | Disable a content source |
| `POST` | `/api/v1/admin/sources/collect` (`/api/v1/sources/collect`) | Firebase Admin Claim (`admin: true`) | Trigger RSS collection across enabled RSS sources and return job summary |
| `GET` | `/api/v1/admin/share-messages` (`/api/v1/share-messages`) | Firebase Admin Claim (`admin: true`) | List generated share messages (supports `status`, `limit`) |
| `GET` | `/api/v1/admin/share-messages/<id>` (`/api/v1/share-messages/<id>`) | Firebase Admin Claim (`admin: true`) | Retrieve a generated share message by ID |
| `PATCH` / `PUT` | `/api/v1/admin/share-messages/<id>` (`/api/v1/share-messages/<id>`) | Firebase Admin Claim (`admin: true`) | Edit a `pending` share message's `title`, `body`, `target_url`, or `status` |

---

## Content Source Administration & SSRF-Safe URL Validation

All content source management endpoints require a verified Firebase administrator token (`@require_admin`).

### Supported Source Types & Extensibility
- **`rss`** (`RssSourceConnector`): Validates and fetches RSS/Atom XML feeds.
- **`official_api`** (`OfficialApiSourceConnector`, alias `api`): Base connector for official REST APIs. Additional official API connectors can be registered via `register_source_connector(connector)` in `app/services/source_connectors.py`.

### Source URL Security Policy (`app/services/url_validator.py`)
1. **Explicit Public Domain Allowlist**: Only hostnames matching `ALLOWED_SOURCE_DOMAINS` (configured via environment variable, supporting exact domains like `feeds.example.com` and subdomain wildcards like `*.example.com`) are permitted. Raw IP literals and unconfigured domains are rejected with `code: "domain_not_allowed"`.
2. **SSRF & Metadata Protection**: Rejects `localhost`, loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`), link-local (`169.254.0.0/16`, `fe80::/10`), and cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`, `fd00:ec2::254`, `100.100.100.200`) across both URL hostnames and DNS-resolved IP addresses (`code: "forbidden_address"`).
3. **Redirect Destination Validation**: Automatic HTTP redirect following is disabled. Each redirect hop (up to `SOURCE_FETCH_MAX_REDIRECTS`, default `3`) has its `Location` target validated against the domain allowlist and SSRF IP/DNS checks before being followed.
4. **Timeouts & Response-Size Limits**: Requests enforce `SOURCE_FETCH_TIMEOUT_SECONDS` (default `5.0`s, returning `code: "source_timeout"` on timeout) and `SOURCE_FETCH_MAX_BYTES` (default `1048576` bytes / 1 MiB, returning `code: "response_too_large"` if exceeded).
