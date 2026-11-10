# Moatok (Content Collection & KakaoTalk Sharing Assistant)

A production-oriented platform comprising:
1. **Python Flask REST API & Cloud Run Backend** (`app/`): Ingests content feeds, persists deduplicated articles and formatted share messages in **Cloud Firestore**, authenticates users via **Firebase Authentication** custom claims, and sends push notifications via **Firebase Cloud Messaging (FCM)**.
2. **Mobile-First Vue 3 PWA** (`frontend/`): Clean, monochrome Progressive Web Application (Vue 3, TypeScript, Vite, Vue Router, Pinia) for reviewing content and initiating user-directed KakaoTalk sharing with System/Light/Dark appearance modes and a bottom navigation bar.

## Architectural Boundary & KakaoTalk Sharing Model

> **Important**: This application **does not** automatically post messages to KakaoTalk Open Chat rooms or personal chats on a user's behalf.
>
> Instead, it follows a **user-initiated sharing workflow**:
> 1. **Collect & Prepare**: The backend ingests content items and formats them into both plain text (`formatted_text`) and a structured template payload (`kakao_share_payload`) tailored for mobile clients.
> 2. **Store**: Prepared messages are persisted in **Cloud Firestore** (`shareable_messages` and `share_messages` collections) with `status: "pending"` and `kakao_shared: false`.
> 3. **Notify**: The backend sends a push notification via **Firebase Cloud Messaging (FCM)** to the user's registered PWA or mobile device(s).
> 4. **User-Initiated Share in Vue 3 PWA / Flutter**: When the user taps the notification or opens the PWA (`frontend/`), the app displays the briefing. The user reviews the content and explicitly triggers KakaoTalk sharing (via Kakao JS SDK, Web Share API, or clipboard), selecting the destination chatroom in KakaoTalk. The client then calls `POST /api/v1/messages/<id>/mark-shared` to record completion.

---

## Project Structure

```text
.
├── app/                            # Python Flask REST API & services
│   ├── __init__.py                 # Flask application factory, logging, CORS, error handlers
│   ├── auth.py                     # Firebase ID token verification, custom claim admin guard & Cloud Scheduler OIDC guard
│   ├── config.py                   # Environment-based configuration (dev, testing, prod)
│   ├── extensions.py               # Firebase Admin & Firestore initialization via ADC
│   ├── models.py                   # Data models & payload validation
│   ├── repositories/
│   │   ├── __init__.py             # Repository exports
│   │   ├── firestore_utils.py      # UTC timestamp normalization, deterministic IDs & secret guards
│   │   ├── sources_repo.py         # `sources` collection repository
│   │   ├── articles_repo.py        # `articles` collection repository (transactional deduplication)
│   │   ├── share_messages_repo.py  # `share_messages` collection repository (transactional deduplication & notification claim)
│   │   └── devices_repo.py         # `users/{userId}/devices` subcollection repository
│   ├── routes/
│   │   ├── health.py               # Public GET /health endpoint
│   │   ├── admin.py                # GET /api/v1/auth/me & /api/v1/admin/* endpoints
│   │   ├── sources.py              # Admin-only /api/v1/admin/sources & /api/v1/sources endpoints
│   │   ├── devices.py              # POST /api/v1/devices/fcm-token
│   │   ├── jobs.py                 # Protected POST /internal/jobs/collect endpoint for Cloud Scheduler
│   │   └── content.py              # /api/v1/messages endpoints
│   └── services/
│       ├── content_service.py           # Content formatting & Firestore persistence
│       ├── notification_service.py      # FCM token registration & push notification dispatch
│       ├── rss_collector.py             # RSS collection service, feed parsing, deduplication & safe logging
│       ├── share_message_generator.py   # Rule-based pending share message generator & length guards
│       ├── source_connectors.py         # RSS and extensible Official API source connectors
│       ├── source_service.py            # Source CRUD orchestration & validation
│       └── url_validator.py             # Domain allowlist, SSRF IP/DNS checks, redirect, timeout & size guards
├── frontend/                       # Mobile-First Vue 3 PWA (TypeScript, Vite, Pinia)
│   ├── .env.production.example     # Production environment variables template
│   ├── public/                     # Static assets, Web App Manifest & icons (PNG & SVG)
│   │   ├── apple-touch-icon.png    # 180x180 iOS Home Screen touch icon
│   │   ├── favicon.png             # 32x32 local PNG favicon
│   │   ├── favicon.svg             # Monochrome vector favicon
│   │   ├── icon-192.svg            # 192x192 vector icon
│   │   ├── icon-512.svg            # 512x512 vector icon
│   │   ├── manifest.webmanifest    # Web App Manifest (standalone, theme colors, icons)
│   │   ├── pwa-192x192.png         # 192x192 local PNG icon (maskable & any)
│   │   └── pwa-512x512.png         # 512x512 local PNG icon (maskable & any)
│   ├── src/
│   │   ├── App.vue                 # App shell with AppHeader, BottomNav & ReloadPrompt
│   │   ├── components/             # BottomNav, AppearanceToggle, MessageCard, ShareModal, ReloadPrompt
│   │   ├── router/                 # Vue Router (Pending, History, Settings, Detail)
│   │   ├── services/               # API, Firebase & Kakao Share services
│   │   ├── stores/                 # Pinia stores (theme, auth, messages, notifications)
│   │   └── views/                  # PendingView, HistoryView, SettingsView, MessageDetailView
│   ├── tests/                      # Vitest unit & component tests (69 tests across 16 files)
│   ├── package.json
│   ├── vite.config.ts              # Vite config with VitePWA & Workbox zero-cache policy
│   └── README.md
├── tests/                          # Backend pytest test suite
│   ├── conftest.py                      # Pytest fixtures & in-memory Firestore/Firebase mocks
│   ├── test_auth.py                     # Auth, expired/invalid tokens, admin custom claims & role-spoofing tests
│   ├── test_fcm_notifications.py        # FCM device registration, concise payloads, invalid token cleanup & observability
│   ├── test_repositories.py             # Firestore repository, UTC, deduplication & secret-rejection tests
│   ├── test_rss_collector.py            # RSS collection, deduplication, fault tolerance & log redaction tests
│   ├── test_scheduler_job.py            # Cloud Scheduler OIDC auth, collection job, retry & concurrency tests
│   ├── test_share_message_generator.py  # Rule-based share message generator, length limits & admin edit tests
│   ├── test_sources.py                  # Admin content source endpoints & SSRF/redirect/timeout/size tests
│   ├── test_health.py                   # Public health endpoint tests
│   ├── test_e2e_workflow.py             # End-to-end 5-stage workflow & Gunicorn/Cloud Run readiness tests
│   └── test_content_and_notifications.py
├── .dockerignore
├── .env.example
├── .firebaserc                     # Firebase CLI project alias configuration
├── .gitignore
├── DEPLOYMENT_FIREBASE.md          # Firebase Hosting deployment guide & 8-point real-device test checklist
├── Dockerfile
├── firebase.json                   # Firebase Hosting configuration (public: frontend/dist, SPA rewrites, cache headers)
├── gunicorn.conf.py                # Gunicorn production configuration (respects PORT)
├── package.json                    # Root build and deployment scripts
├── requirements.txt
└── wsgi.py                         # WSGI entrypoint for Gunicorn
```

---

## Progressive Web App (PWA) Architecture & Mobile Installation

The frontend (`frontend/`) is built with Vue 3, TypeScript, and `vite-plugin-pwa` to provide a mobile-first, high-contrast monochrome application that functions seamlessly across Android and iOS devices.

### 1. Web App Manifest & App Identity
The manifest ([`manifest.webmanifest`](frontend/public/manifest.webmanifest)) and HTML meta tags configure a standalone app experience:
- **App Name**: `Moatok · 카카오톡 공유 비서`
- **Short Name**: `Moatok`
- **Display Mode**: `standalone` (removes browser URL bar and toolbar chrome)
- **Theme & Background Color**: `#000000` (deep OLED-friendly monochrome)
- **Icons**:
  - `pwa-192x192.png`: 192x192 local PNG icon (`purpose: "any maskable"`)
  - `pwa-512x512.png`: 512x512 local PNG icon (`purpose: "any maskable"`)
  - `apple-touch-icon.png`: 180x180 local PNG icon optimized for iOS Safari Home Screen
  - `favicon.png` (32x32) & `favicon.svg` (vector)
  - `icon-192.svg` & `icon-512.svg`: Scalable monochrome vector icons

### 2. Service Worker Caching & Zero-Cache API Policy
Configured in [`vite.config.ts`](frontend/vite.config.ts) via `VitePWA` and Workbox:
- **Safe Application Shell Pre-caching**:
  - Pre-caches core assets (`**/*.{js,css,html,ico,png,svg,webmanifest}`) with content hashes.
  - Purges outdated revisions on service worker activation (`cleanupOutdatedCaches: true`).
- **Zero-Cache Policy for Authenticated API & Sensitive Data**:
  - Navigation denylist: `navigateFallbackDenylist: [/^\/api\//, /^\/health/, /^\/internal\//]`.
  - Explicit runtime routing: `NetworkOnly` for `/^\/api\/.*/`, `/^\/health$/`, and `/^\/internal\/.*/`.
  - **Security Guarantee**: Authenticated API responses (user messages, device tokens, Firebase ID tokens, admin endpoints) are **strictly network-only and never stored** in CacheStorage or IndexedDB.

### 3. Update Prompt (`ReloadPrompt.vue`)
- Configured with `registerType: 'prompt'`.
- The [`ReloadPrompt.vue`](frontend/src/components/ReloadPrompt.vue) component monitors the service worker lifecycle via `virtual:pwa-register/vue` (`needRefresh`, `updateServiceWorker`).
- When a new deployment is detected, an unobtrusive monochrome toast appears at the top of the mobile screen alerting the user: *"새로운 버전이 출시되었습니다."* Clicking **"업데이트"** activates the waiting service worker and reloads the page with the latest version.

### 4. Platform Installation Instructions (Android & iOS)

#### Android (Chrome / Samsung Internet)
1. Navigate to the app in Chrome or Samsung Internet.
2. Tap the browser menu (**⋮**) or the install banner.
3. Select **"Install app"** or **"Add to Home screen"** (**앱 설치** / **홈 화면에 추가**).
4. Moatok will be installed as a standalone application in the app drawer and home screen.

#### iOS / iPadOS (Safari)
> [!IMPORTANT]
> **iOS Version & Home Screen Execution Requirements**:
> 1. **iOS 16.4+ Required for Web Push**: Apple introduced Web Push Notification support for PWAs starting in iOS 16.4. Older iOS versions do not support the Web Push API.
> 2. **Must Be Launched from Home Screen**: Web Push notification permissions (`Notification.requestPermission()`) and standalone display **only function when the PWA is launched from the iOS Home Screen**. In regular Safari browser tabs, Web Push is disabled by Apple security policy.

**Step-by-Step iOS Installation**:
1. Open the application in **Safari** (third-party in-app browsers like KakaoTalk or Instagram in-app browser do not support PWA installation).
2. Tap the **Share icon** (square with upward arrow) in the Safari toolbar.
3. Scroll down and select **"Add to Home Screen"** (**홈 화면에 추가**).
4. Tap **"Add"** in the top-right corner.
5. Exit Safari and open **Moatok** directly from the Home Screen icon.
6. In **Settings** (`/settings`), tap **"푸시 알림 권한 허용하기"** to grant notification permissions.

### 5. Security Context Requirements: HTTPS & Localhost
Per W3C Service Worker and Web App Manifest specifications:
- **Production Requirements**: Must be served over **HTTPS** with a valid TLS certificate. If served over plain HTTP on a public domain or remote LAN IP (e.g. `http://192.168.x.x`), browsers will refuse to register the Service Worker or enable Web Push notifications.
- **Localhost Development**: Modern browsers treat `http://localhost` and `http://127.0.0.1` as secure contexts, allowing local PWA and service worker development without SSL certificates.

### 6. Vue 3 PWA Client Authentication & Token Lifecycle
- **Configurable Sign-in Methods**: Configured via `VITE_FIREBASE_AUTH_SIGN_IN_METHOD` (`email`, `anonymous`, `google`, default: `email`) with dedicated UI components for email/password, anonymous guest browsing, and Google authentication.
- **Pinia State Machine (`useAuthStore`)**: Manages `status` (`'loading' | 'authenticated' | 'signed_out' | 'expired' | 'error'`), verified backend user claims (`isAdmin`), and localized error messages.
- **Automatic Bearer Token Injection**: All outgoing requests in [`frontend/src/services/api.ts`](frontend/src/services/api.ts) automatically attach `Authorization: Bearer <ID_TOKEN>`.
- **401 Token Refresh & Session Recovery**: If an API response returns `401 Unauthorized` with `code: "token_expired"`, the client interceptor forces a token refresh (`getIdToken(true)`) and retries the request once before signaling session expiration.
- **Zero Secrets on Client**: The frontend uses only public Firebase client web config. No private keys, service account JSON files, or Kakao client secrets are present in frontend bundles or repository code.

### 7. Official Kakao SDK Integration & Developer Console Settings

The Vue 3 PWA integrates the official **Kakao SDK for JavaScript (v2.7.2)** for user-directed KakaoTalk sharing.

#### Kakao Developers Console Settings Guide
1. **Application Registration**:
   - Register an application in the [Kakao Developers Console](https://developers.kakao.com/).
   - Copy the **JavaScript Key** ([앱 설정] > [요약 정보] > [JavaScript 키]).
   - Set `VITE_KAKAO_JAVASCRIPT_KEY` in `frontend/.env`.
2. **Web Platform & Site Domain Registration (CRITICAL KOE101 Prevention)**:
   - Navigate to **[앱 설정] > [플랫폼] > [Web 플랫폼 등록]**.
   - Register all web domains hosting Moatok:
     - Development: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:8080`
     - Production: `https://moatok.example.com`, `https://<project-id>.web.app`
   - **Official Domain Validation Constraint**: Kakao JavaScript SDK strictly rejects any link targets (`mobileWebUrl`, `webUrl`) that do not belong to registered platform domains with error `KOE101 (Unregistered domain)`.
   - **Moatok Solution**: Template links point to the application's registered domain detail route (`${window.location.origin}/messages/${message.id}`). The shared detail page on the registered domain provides the direct link (`target_url`) to the original article source.

#### Supported Templates & Fallback Chain
- **Feed Template (`feed`)**: Used when the briefing contains an image URL; includes title, description, image, and action button.
- **Text Template (`text`)**: Used when no image is present; includes title, formatted body, and action button.
- **Graceful Fallbacks**: If Kakao SDK is blocked, uninitialized, or encounters errors, the client falls back to the **Web Share API** (`navigator.share`) and standard **Clipboard Copy** (`navigator.clipboard.writeText`).

#### Share Initiation Telemetry vs Delivery Decoupling
- **User-Initiated Share Only**: Sharing starts strictly after the user clicks the prominent "카카오톡으로 공유하기" button.
- **Backend Telemetry**: When sharing is initiated, the PWA reports the attempt to the Flask backend (`POST /api/v1/messages/<id>/share-attempt`).
- **No False Delivery Claims**: Clicking the share button **does not** mark the message as delivered or shared. The status remains `pending`. Delivery confirmation is decoupled and requires explicit user action (`POST /api/v1/messages/<id>/mark-shared`).

#### Real-Device Open Chat Testing Requirement
- **Mobile Hardware Required**: Kakao Open Chat room selection is available **only within the native KakaoTalk mobile app on a physical Android or iOS device**. Desktop browsers and simulators cannot verify Open Chat room selection.

#### Strict Prohibition of Private Protocols and Automation
- Strictly no undocumented or reverse-engineered internal Kakao schemes (`kakaotalk://` RPCs).
- Strictly no background accessibility services, UI automation, or bot scraping.
- Complies fully with Kakao developer platform policies.

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

- **Never commit secrets or service account JSON files**: `.gitignore` and `.dockerignore` exclude `.env`, `.env.*`, `*.pem`, `*.key`, `*service-account*.json`, `*credentials*.json`, and `firebase-adminsdk-*.json`. Furthermore, `assert_no_forbidden_secrets()` in `app/repositories/firestore_utils.py` rejects any attempt to persist Kakao access/refresh tokens or service account private keys in Firestore.
- **Deployed Environments (Cloud Run)**: Leave `GOOGLE_APPLICATION_CREDENTIALS` unset. The backend initializes `firebase_admin` with `credentials.ApplicationDefault()`, which automatically uses the Cloud Run service's attached least-privilege Google Cloud service account.
- **Local Development**: Authenticate with Google Cloud Application Default Credentials (`gcloud auth application-default login`) or run against local Firebase/Firestore emulators.

---

## Required Firebase & Google Cloud Configuration

### 1. Required Google Cloud APIs
Enable the required APIs in your Google Cloud project:
```bash
PROJECT_ID="your-gcp-project-id"

gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  identitytoolkit.googleapis.com \
  fcm.googleapis.com \
  --project="${PROJECT_ID}"
```

### 2. Cloud Firestore Configuration
Create a **Firestore Native Mode** database in your target region:
```bash
gcloud firestore databases create \
  --project="${PROJECT_ID}" \
  --database="(default)" \
  --location="asia-northeast3" \
  --type="firestore-native"
```
The application uses the following collections (all timestamps stored in UTC):
- `sources` (`FIRESTORE_COLLECTION_SOURCES`): Content source definitions (`name`, `url`, `source_type`, `enabled`, `last_checked_at`, `created_at`).
- `articles` (`FIRESTORE_COLLECTION_ARTICLES`): Collected articles deduplicated via deterministic IDs (`source_id`, `source_url`, `canonical_url`, `stable_id`, `title`, `summary`, `published_at`, `collected_at`).
- `share_messages` (`FIRESTORE_COLLECTION_SHARE_MESSAGES`): Rule-based shareable messages (`article_id`, `title`, `body`, `target_url`, `status`, `notification_attempts`, `kakao_shared`, `created_at`, `updated_at`).
- `users/{userId}/devices` (`FIRESTORE_COLLECTION_USERS` / `FIRESTORE_SUBCOLLECTION_DEVICES`): Per-user registered Flutter device FCM tokens.

### 3. Firebase Authentication & Cloud Messaging (FCM)
1. Link your Google Cloud project in the **Firebase Console**.
2. Enable **Firebase Authentication** sign-in providers used by the Flutter client.
3. Assign administrator privileges strictly via **Firebase Custom User Claims** (`{"admin": true}`) using the Firebase Admin SDK (see [Assigning an Administrator Custom Claim Securely](#4-assigning-an-administrator-custom-claim-securely)).
4. Enable **Firebase Cloud Messaging (FCM API v1)** so the backend can send concise push notifications (`share_message_id` only) to registered Flutter devices.

### 4. Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8080` | TCP port injected by Cloud Run; respected by `gunicorn.conf.py`, `Dockerfile`, and `wsgi.py` |
| `FLASK_ENV` | `production` (in Docker) | `development`, `testing`, or `production` |
| `GOOGLE_CLOUD_PROJECT` | — | Google Cloud project ID for Firestore & ADC |
| `FIREBASE_PROJECT_ID` | `GOOGLE_CLOUD_PROJECT` | Firebase project ID for ID token & FCM verification |
| `FIRESTORE_DATABASE` | `(default)` | Firestore database ID |
| `SCHEDULER_SERVICE_ACCOUNT_EMAIL` | — | **Required for `/internal/jobs/collect`**: Expected Cloud Scheduler service account email (fails closed with `403` if unset) |
| `SCHEDULER_OIDC_AUDIENCE` | — | Expected `aud` claim on Cloud Scheduler OIDC tokens (e.g., `https://<service-url>/internal/jobs/collect`) |
| `ALLOWED_SOURCE_DOMAINS` | — | Comma-separated public domain allowlist for RSS/API sources (e.g. `feeds.example.com,*.example.org`) |
| `SOURCE_FETCH_TIMEOUT_SECONDS` | `5.0` | HTTP request timeout in seconds when validating/fetching sources |
| `SOURCE_FETCH_MAX_BYTES` | `1048576` (1 MiB) | Maximum response body size in bytes when fetching sources |
| `SOURCE_FETCH_MAX_REDIRECTS` | `3` | Maximum SSRF-validated redirect hops allowed |
| `SHARE_MESSAGE_PREFIX` | `[모아톡 브리핑]` | Configurable prefix prepended to generated share messages |
| `SHARE_MESSAGE_MAX_TITLE_LENGTH` | `100` | Maximum title length in generated share messages |
| `SHARE_MESSAGE_MAX_DESCRIPTION_LENGTH` | `160` | Maximum summary/description length in generated share messages |
| `SHARE_MESSAGE_MAX_BODY_LENGTH` | `500` | Maximum total body length (preserving the article URL) |
| `GUNICORN_WORKERS` | `2` | Number of Gunicorn worker processes |
| `GUNICORN_THREADS` | `4` | Number of threads per Gunicorn worker |
| `GUNICORN_TIMEOUT` | `60` | Gunicorn worker timeout in seconds |

---

## Local Setup & Testing Instructions (Mocks & Emulators)

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
```

### 2. Run Offline Automated Tests (Mocks & Fake Repositories)

The automated test suite (`pytest`) runs 100% offline in `testing` mode without any external network calls or cloud credentials. It uses:
- `FakeFirestoreClient` & `FakeTransaction` (`tests/conftest.py`) to test transactional deduplication and concurrency.
- Mocked Firebase Auth (`mock_firebase_auth`), mocked Google OIDC (`mock_scheduler_oidc`), and mocked FCM (`mock_fcm_send`).
- Mocked HTTP openers (`SyntheticProbeResponse` / `_MockHttpResponse`) to test RSS parsing, SSRF blocking, redirects, timeouts, and size limits.

```bash
.venv/bin/pytest -v
```

### 3. Local Testing with Firebase / Firestore Emulators

To test locally against the official **Google Cloud Firestore Emulator** and **Firebase Auth Emulator** instead of cloud resources:

1. Start the local emulators (using the Firebase CLI or `gcloud emulators firestore start`):
   ```bash
   gcloud beta emulators firestore start --host-port=127.0.0.1:8085
   ```
2. Export the emulator environment variables and run the Flask/Gunicorn server:
   ```bash
   export FLASK_ENV=development
   export GOOGLE_CLOUD_PROJECT=demo-moatok-local
   export FIREBASE_PROJECT_ID=demo-moatok-local
   export FIRESTORE_EMULATOR_HOST=127.0.0.1:8085
   export ALLOWED_SOURCE_DOMAINS=example.com,feeds.example.com
   export PORT=8080

   .venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
   ```
3. Verify the health endpoint:
   ```bash
   curl http://localhost:8080/health
   ```

### 4. Local Docker Build & Gunicorn `PORT` Verification

Verify that the container runs as non-root (`appuser`), uses Gunicorn, and respects a custom `PORT` environment variable (e.g., `PORT=9090`):

```bash
docker build -t moatok-backend .
docker run --rm -p 9090:9090 -e PORT=9090 --env-file .env moatok-backend
curl http://localhost:9090/health
```

---

## Google Cloud Run Deployment (Least-Privilege IAM)

### 1. Dedicated Service Accounts & Least-Privilege IAM Permissions

Never use the default Compute Engine service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`) or grant broad primitive roles (`roles/owner`, `roles/editor`). Instead, provision **two** dedicated service accounts with minimal permissions:

| Service Account | Purpose | Least-Privilege IAM Roles | Scope |
| :--- | :--- | :--- | :--- |
| `moatok-cloudrun-sa@<PROJECT_ID>.iam.gserviceaccount.com` | **Cloud Run Runtime Identity** (attached to the Cloud Run revision via ADC) | `roles/datastore.user` (Firestore read/write)<br>`roles/firebaseauth.admin` (verify Firebase ID tokens & manage custom claims)<br>`roles/cloudmessaging.admin` or custom role with `cloudmessaging.messages.create` (send FCM push notifications)<br>`roles/logging.logWriter` (write container logs) | Project |
| `moatok-scheduler@<PROJECT_ID>.iam.gserviceaccount.com` | **Cloud Scheduler Invoker Identity** (mints OIDC tokens for `POST /internal/jobs/collect`) | `roles/run.invoker` (invoke the Cloud Run service) | `moatok-backend` Cloud Run service only |

Create the Cloud Run runtime service account and bind its least-privilege roles:
```bash
PROJECT_ID="your-gcp-project-id"
REGION="asia-northeast3"
SERVICE_NAME="moatok-backend"
RUNTIME_SA_NAME="moatok-cloudrun-sa"
RUNTIME_SA_EMAIL="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "${RUNTIME_SA_NAME}" \
  --project="${PROJECT_ID}" \
  --display-name="Moatok Cloud Run Runtime Service Account"

for ROLE in \
  "roles/datastore.user" \
  "roles/firebaseauth.admin" \
  "roles/firebase.sdkAdminServiceAgent" \
  "roles/logging.logWriter"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
    --role="${ROLE}"
done
```

### 2. Build & Push Container Image to Artifact Registry

```bash
REPO_NAME="moatok"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:latest"

gcloud artifacts repositories create "${REPO_NAME}" \
  --project="${PROJECT_ID}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Moatok container repository"

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --tag="${IMAGE_URI}" .
```

### 3. Deploy to Cloud Run with the Dedicated Runtime Service Account

```bash
SCHEDULER_SA_NAME="moatok-scheduler"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_URI}" \
  --service-account="${RUNTIME_SA_EMAIL}" \
  --port=8080 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=60s \
  --set-env-vars="FLASK_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},FIREBASE_PROJECT_ID=${PROJECT_ID},SCHEDULER_SERVICE_ACCOUNT_EMAIL=${SCHEDULER_SA_EMAIL},ALLOWED_SOURCE_DOMAINS=feeds.example.com" \
  --allow-unauthenticated
```
*(Note: `--allow-unauthenticated` allows public HTTPS traffic to reach `/health` and Firebase-authenticated `/api/v1/*` mobile endpoints, while `/internal/jobs/collect` remains strictly locked down by `@require_scheduler_auth` OIDC verification. If the Cloud Run service itself is deployed with `--no-allow-unauthenticated`, Cloud Run additionally enforces `roles/run.invoker` at the ingress proxy layer.)*

After initial deployment, retrieve the canonical Cloud Run service URL and lock `SCHEDULER_OIDC_AUDIENCE` to `<SERVICE_URL>/internal/jobs/collect`:
```bash
SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
JOB_AUDIENCE="${SERVICE_URL}/internal/jobs/collect"

gcloud run services update "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --update-env-vars="SCHEDULER_OIDC_AUDIENCE=${JOB_AUDIENCE}"
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
| `POST` | `/api/v1/admin/share-messages/<id>/notify` (`/api/v1/share-messages/<id>/notify`) | Firebase Admin Claim (`admin: true`) | Send a concise FCM notification for a pending share message and record observable attempt telemetry |
| `POST` | `/internal/jobs/collect` | Google OIDC Token (`@require_scheduler_auth`) | Protected Cloud Scheduler job that collects enabled sources, creates deduplicated articles & pending share messages, notifies registered users, and returns a structured job summary |

---

## Cloud Scheduler & Cloud Run Authentication (`POST /internal/jobs/collect`)

The scheduled collection endpoint (`POST /internal/jobs/collect` in `app/routes/jobs.py`) is **never exposed unauthenticated**. It is protected by `@require_scheduler_auth` (`app/auth.py`), which enforces two layers of defense:
1. **Cloud Run IAM / Ingress Protection**: Cloud Run verifies the Google-signed OIDC token at the platform boundary (`roles/run.invoker`).
2. **Application-Level OIDC & Service Account Verification**: The Flask application independently verifies the `Authorization: Bearer <OIDC_ID_TOKEN>` signature, expiration, issuer (`accounts.google.com` / `https://accounts.google.com`), audience (`SCHEDULER_OIDC_AUDIENCE`), and verified `email` claim against `SCHEDULER_SERVICE_ACCOUNT_EMAIL` using `google.oauth2.id_token.verify_oauth2_token()`. If `SCHEDULER_SERVICE_ACCOUNT_EMAIL` is unset, the endpoint **fails closed** with `403 Forbidden` (`code: "scheduler_auth_not_configured"`).

### Idempotency, Retry Tolerance & Concurrency Safety
- **Deterministic Article IDs**: Articles use `build_article_doc_id(source_id, canonical_url, stable_id)` (`art_<sha256[:32]>`) and a Firestore transaction (`ArticleRepository.create_or_get_with_status`) so retries or overlapping runs never create duplicate articles.
- **Deterministic Share Message IDs**: Share messages use `build_share_message_doc_id(article_id)` (`smsg_<sha256[:32]>`) and a Firestore transaction (`ShareMessageRepository.create_or_get_for_article_with_status`). Even if a previous run saved an article and crashed before saving its share message, the next retry ensures the pending share message is created.
- **Transactional Initial Notification Claim**: `ShareMessageRepository.claim_initial_notification(message_id)` uses a Firestore transaction to atomically set `initial_notification_claimed = True` once per share message so retries and concurrent workers never send duplicate initial FCM push notifications.

### Step-by-Step Cloud Run & Cloud Scheduler Configuration

#### 1. Create a Dedicated Cloud Scheduler Service Account
```bash
PROJECT_ID="your-gcp-project-id"
REGION="asia-northeast3"
SERVICE_NAME="moatok-backend"
SCHEDULER_SA_NAME="moatok-scheduler"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "${SCHEDULER_SA_NAME}" \
  --project="${PROJECT_ID}" \
  --display-name="Moatok Cloud Scheduler Invoker"
```

#### 2. Deploy Cloud Run with `SCHEDULER_SERVICE_ACCOUNT_EMAIL` and `SCHEDULER_OIDC_AUDIENCE`
Deploy the Cloud Run service and configure the expected scheduler service account email and OIDC token audience:
```bash
SERVICE_URL="https://${SERVICE_NAME}-<hash>-an.a.run.app"
JOB_AUDIENCE="${SERVICE_URL}/internal/jobs/collect"

gcloud run services update "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --set-env-vars="SCHEDULER_SERVICE_ACCOUNT_EMAIL=${SCHEDULER_SA_EMAIL},SCHEDULER_OIDC_AUDIENCE=${JOB_AUDIENCE}"
```

#### 3. Grant `roles/run.invoker` to the Scheduler Service Account
```bash
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --member="serviceAccount:${SCHEDULER_SA_EMAIL}" \
  --role="roles/run.invoker"
```

#### 4. Create the Cloud Scheduler HTTP Job with OIDC Authentication
Configure Cloud Scheduler to mint an OIDC ID token for `SCHEDULER_SA_EMAIL` with `--oidc-token-audience` matching `SCHEDULER_OIDC_AUDIENCE`:
```bash
gcloud scheduler jobs create http moatok-collect-rss \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="*/15 * * * *" \
  --uri="${SERVICE_URL}/internal/jobs/collect" \
  --http-method=POST \
  --oidc-service-account-email="${SCHEDULER_SA_EMAIL}" \
  --oidc-token-audience="${JOB_AUDIENCE}" \
  --max-retry-attempts=3 \
  --min-backoff=10s \
  --max-backoff=120s
```

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

---

## End-to-End (E2E) Test Plan

This test plan covers the full lifecycle across **Collection**, **Deduplication**, **Firestore Persistence**, **FCM Notification**, and **User-Initiated KakaoTalk Sharing** (automated in `tests/test_e2e_workflow.py` and verifiable in staging/production).

### Stage 1: Content Source Registration & Scheduled RSS Collection
1. **Admin Source Creation**:
   - Send `POST /api/v1/admin/sources` with an administrator Firebase ID token (`{"admin": true}` custom claim) and payload `{"name": "Briefing RSS", "url": "https://feeds.example.com/rss.xml", "source_type": "rss", "enabled": true}`.
   - **Expected**: `201 Created`; SSRF validator confirms the domain is in `ALLOWED_SOURCE_DOMAINS`, resolves to a public IP, and responds within timeout/size bounds.
   - Verify non-admin tokens receive `403 Forbidden` (`code: "admin_required"`) and private/metadata URLs (`127.0.0.1`, `169.254.169.254`, `metadata.google.internal`) are rejected with `400 Bad Request` (`code: "forbidden_address"`).
2. **Cloud Scheduler Job Trigger**:
   - Trigger `POST /internal/jobs/collect` with a valid Cloud Scheduler OIDC Bearer token for `SCHEDULER_SERVICE_ACCOUNT_EMAIL`.
   - **Expected**: `200 OK` with structured job summary (`sources_checked`, `sources_succeeded`, `processed`, `new`, `duplicate`, `failed`, `share_messages_created`, `notifications`).
   - Verify requests without a token return `401` (`code: "missing_token"`), invalid/expired OIDC tokens return `401` (`code: "invalid_scheduler_token"`), and unexpected service accounts return `403` (`code: "unauthorized_service_account"`).

### Stage 2: Deduplication, Retries & Concurrent Execution
1. **In-Feed & Cross-Run Deduplication**:
   - Include feed items that share the same `<guid>` (`stable_id`) or resolve to the same `canonical_url` after stripping tracking parameters (`utm_*`, `fbclid`, `gclid`).
   - Re-run `POST /internal/jobs/collect` immediately with the same RSS feed.
   - **Expected**: First run records `new: N`, `share_messages_created: N`; second run records `new: 0`, `duplicate: N`, `share_messages_created: 0`, `notifications.messages_notified: 0`.
2. **Partial Retry & Concurrent Execution**:
   - Trigger concurrent `POST /internal/jobs/collect` requests across multiple worker threads (`tests/test_scheduler_job.py`).
   - **Expected**: Firestore transactions (`ArticleRepository.create_or_get_with_status`, `ShareMessageRepository.create_or_get_for_article_with_status`, `ShareMessageRepository.claim_initial_notification`) guarantee exactly 1 article document, 1 pending share message document, and 1 initial notification dispatch per unique article.

### Stage 3: Firestore Persistence & Data Hygiene
1. **Collection & Field Verification**:
   - Inspect `sources`, `articles`, `share_messages`, and `users/{userId}/devices` in Firestore.
   - **Expected**:
     - All timestamp fields (`created_at`, `last_checked_at`, `published_at`, `collected_at`, `updated_at`) are persisted in UTC (`tzinfo=timezone.utc`).
     - Generated share messages have initial `status: "pending"`, `kakao_shared: false`, configurable prefix (`SHARE_MESSAGE_PREFIX`), bounded title/description/body lengths, and the original `target_url`.
     - `assert_no_forbidden_secrets` blocks any document containing Kakao OAuth tokens (`kakao_access_token`, `kakao_refresh_token`) or service account private keys (`private_key`, `private_key_id`).

### Stage 4: Firebase Cloud Messaging (FCM) Notification & Token Lifecycle
1. **Device Token Registration**:
   - Send `POST /api/v1/devices/fcm-token` with a user's Firebase Bearer token and `{"fcm_token": "<token>", "device_id": "<device_id>", "platform": "ios"}`.
   - **Expected**: `200 OK`; token is upserted under `users/{userId}/devices/{deviceId}` with `enabled: true`.
2. **Concise Push Notification & Observability**:
   - When `POST /internal/jobs/collect` or `POST /api/v1/admin/share-messages/<id>/notify` runs, inspect the dispatched FCM message and the updated `share_messages/<id>` document.
   - **Expected**:
     - FCM `data` payload contains only `{"action": "OPEN_SHARE_PREVIEW", "share_message_id": "<id>", "message_id": "<id>", "sharing_mode": "user_initiated_flutter"}` — **never** full article text, user PII, or credentials.
     - Firestore records `notification_attempts`, `last_notification_status`, and `last_notified_at`, while `kakao_shared` remains `false` and `status` remains `"pending"` (proving notification delivery is never conflated with KakaoTalk sharing).
     - Invalid or expired tokens raising `UnregisteredError` / `InvalidArgumentError` are automatically deactivated (`enabled: false`).

### Stage 5: User-Initiated KakaoTalk Sharing & Completion
1. **Optional Admin Review / Edit**:
   - Admin sends `PATCH /api/v1/admin/share-messages/<id>` while `status == "pending"` to refine `title` or `body`.
   - **Expected**: `200 OK` with updated content validated against length limits.
2. **Flutter / PWA Share Preview & User-Initiated KakaoTalk Share**:
   - When the user taps the FCM notification or opens the PWA (`frontend/`), the app calls `GET /api/v1/messages/<share_message_id>` with the user's Firebase ID token to display the share preview.
   - After the user explicitly completes sharing via the KakaoTalk Web/Flutter SDK / native share sheet, the app calls `POST /api/v1/messages/<share_message_id>/mark-shared` with `{"share_channel": "kakaotalk_web_sdk"}` (or `"kakaotalk_flutter_sdk"`).
   - **Expected**: `200 OK`; document transitions to `status: "shared"`, `kakao_shared: true`, `shared_by_user_id: "<uid>"`, and `shared_by_user_at: "<ISO-8601 UTC timestamp>"`.

---

## Firebase Hosting Deployment (Vue 3 PWA)

For full step-by-step instructions and technical reference, see **[DEPLOYMENT_FIREBASE.md](DEPLOYMENT_FIREBASE.md)**.

### 1. Build and Deploy
```bash
# Build production bundle with TypeScript type checks
npm run build:prod

# Deploy static PWA assets and routing configuration to Firebase Hosting
npm run deploy:hosting
# or: firebase deploy --only hosting
```

### 2. SPA Route Fallback & Cache-Control Policy ([`firebase.json`](firebase.json))
- **SPA Rewrites**: `{"source": "**", "destination": "/index.html"}` guarantees that direct visits or refreshes on `/messages/:id`, `/history`, and `/settings` resolve through Vue Router rather than returning 404 from the CDN.
- **Service Worker Updates**: `/sw.js` is served with `Cache-Control: no-cache, no-store, must-revalidate` to ensure mobile clients immediately fetch updated service worker scripts.
- **Static Assets**: `/assets/**` are generated with content hashes and cached with `public, max-age=31536000, immutable`.

### 3. Environment-Specific API Configuration
- Configured in `frontend/.env.production` (see `frontend/.env.production.example`).
- **Option A (Direct Cloud Run URL)**: `VITE_API_BASE_URL=https://moatok-backend-your-project-id.asia-northeast3.run.app`
- **Option B (Same-Origin Rewrite)**: Set `VITE_API_BASE_URL=` and route `/api/**` to Cloud Run directly in `firebase.json`.

### 4. Kakao Developers Console Web Site Domain Registration (`KOE101` Prevention)
The official Kakao JavaScript SDK verifies that all template link parameters (`webUrl`, `mobileWebUrl`) belong to registered domains. Register the deployed domain under **[내 애플리케이션] > [앱 설정] > [플랫폼] > [Web] > [사이트 도메인]**:
- `https://<your-project-id>.web.app`
- `https://<your-project-id>.firebaseapp.com`
- Any custom production domains (e.g., `https://moatok.example.com`)

### 5. Firebase Authentication Authorized Domains
Ensure your deployment domains are listed under **[Firebase Console] > [Authentication] > [Settings] > [Authorized domains]** to authorize Google Sign-in and redirect/popup handlers.

### 6. Real-Device Test Checklist (Android & iOS)
Follow the 8-point physical device verification plan detailed in [DEPLOYMENT_FIREBASE.md](DEPLOYMENT_FIREBASE.md):
1. **Open deployed PWA over HTTPS** (`https://<project-id>.web.app`).
2. **Add to Home Screen** (Android Chrome install banner / iOS Safari Share > "Add to Home Screen").
3. **Sign in** (Email, Google, or Anonymous) and verify ID token attachment (`Authorization: Bearer <token>`).
4. **Receive a test push notification** (noting that iOS Web Push strictly requires Home Screen installation on iOS 16.4+).
5. **Open a share message** (verify deep-linking, details rendering, and SPA refresh fallback).
6. **Launch KakaoTalk sharing** (verify Kakao SDK initialization without `KOE101`, or graceful fallback).
7. **Check Open Chat room selection in KakaoTalk** (confirm selection on physical mobile device).
8. **Confirm delivery information received by backend** (verify `POST /api/v1/messages/:id/share-attempt` telemetry vs `POST /api/v1/messages/:id/mark-shared` user-confirmed status decoupling).

### English scraper integration

Moatok imports saved lessons from `https://english-scrapper.onrender.com`; it does
not run OCR or trigger upstream scraping. Set `ENGLISH_SCRAPER_ENABLED=true` to
include a bounded 20-record page in each existing scheduler collection run.
Scheduled runs persist the next offset and restart at zero after scanning the
catalog, so later corrections and previously failed records are revisited.
Offset pagination is eventually consistent; repeat scans repair shifts caused by
new upstream records. An upstream incremental cursor is not currently available.

Administrators can use **Settings → 오늘의 영어** to import pages or inspect held
lessons. API controls (Firebase admin token required):

- `GET /api/v1/admin/integrations/english-scrapper`: configuration and last sync.
- `POST /api/v1/admin/integrations/english-scrapper/sync`, JSON `{"offset":0}`:
  imports one page and returns `next_offset`, counts and per-record errors.
- `GET /api/v1/admin/integrations/english-scrapper/lessons`: up to 100 imported
  lesson snapshots, including `missing_sections` for review.

Imports use stable external IDs and existing transactional message creation.
Snapshots in `english_lessons` retain structured fields, upstream update time and
content hash. Existing share text is preserved on upstream corrections to protect
user edits and shared messages. Detail pages display the latest imported fields.
Incomplete lessons or uncertain OCR do not produce new share messages or pushes;
correct the lesson upstream and sync again to release it automatically.
`GET /api/v1/share-messages/{id}/english-lesson` provides the structured lesson to
signed-in users with access to the shared message catalog.

The existing FCM and user-initiated Kakao sharing flow is reused. No upstream
credentials are needed for the deployed read API. Deployment and enabling the
scheduled integration are separate from these source changes.

Anyone can enter a Chosun English article or section URL in Settings → 오늘의 영어.
Use **+ URL 추가** to add up to 20 URLs. Fetch processes unique URLs sequentially,
shows each result, and continues if an individual URL fails.

Public Fetch calls `https://english-scrapper.onrender.com/api/v1/lessons/fetch`
directly, without Firebase authentication or a Moatok backend. The scraper allows
Moatok's Hosting origins through CORS. Section URLs resolve to the newest listed
lesson; article URLs extract that article. Extraction does not depend on Firestore.
These results are displayed in the form, not saved to Moatok's sharing queue.
The separate admin/scheduled import pipeline above still requires a Moatok backend
and working persistent storage. Set `VITE_ENGLISH_SCRAPER_URL` at build time to
change the upstream service, and allow the corresponding frontend origin there.

### Send to My Chat

Cards, message details and share previews provide **나와의 채팅에 보내기**.
Connect the Kakao account, review the exact preview (text is limited to 200
characters), then press **확인 후 전송**. Only Kakao's `result_code: 0` is treated as
success; this does not mark a card as delivered to an Open Chat room. Sending
has no automatic retry. The user must inspect My Chat if delivery is uncertain.

Register a Kakao Developers app, enable Kakao Login and `talk_message` consent,
register the frontend domain for JavaScript SDK and Product Link, and register
the backend `/api/v1/kakao/callback` redirect URI. Set the public
`VITE_KAKAO_JAVASCRIPT_KEY` at build time. Configure server-only
`FLASK_SECRET_KEY` (a strong random value), `KAKAO_REST_API_KEY`,
`KAKAO_CLIENT_SECRET` if required by the app, `KAKAO_REDIRECT_URI` and
`KAKAO_FRONTEND_ORIGIN`. Deploy this Flask backend and configure
`VITE_API_BASE_URL` accordingly. The OAuth popup connects directly to that backend;
it requires HTTPS and returns the access token only to the configured frontend
origin using postMessage. Access tokens remain in memory. The deployed Render bridge maintains a persistent,
authenticated-encryption cookie containing the refresh session; only the server
can decrypt it. The cookie is Secure, HttpOnly, host-only and SameSite=Lax.
A short first-party popup restores the session across reloads, avoiding reliance
on third-party cookies. Refresh tokens rotate when Kakao provides a replacement.
The encryption key is derived with domain separation from KAKAO_SESSION_SECRET
or the existing server-side KAKAO_CLIENT_SECRET; changing it invalidates sessions.
Settings provides connect/restore and disconnect controls. Disconnect clears
the cookie and attempts to revoke the current Kakao tokens. Clearing browser
cookies, expired refresh tokens, or revocation requires connecting again. No analytics or Firebase login is required for
this separate Kakao account connection.

Without the registered app and deployed OAuth backend, the UI reports a setup
error; Firebase Hosting alone cannot exchange Kakao authorization codes.

Production My Chat OAuth is hosted on `english-scrapper.onrender.com` using its
`/api/v1/kakao/status`, `/login` and `/callback` endpoints. Configure
`VITE_KAKAO_API_BASE_URL=https://english-scrapper.onrender.com` independently of
Moatok's other REST APIs. The deployed frontend uses the Moatok app JavaScript
key in the ignored `frontend/.env.production.local` file. Any other build system
must supply that public key and OAuth base URL too. The REST key and client
secret are configured only in Render's environment. Product links and the
JavaScript SDK domain are registered for `https://moatalk-e6fe1.web.app`.

### Fetched cards in Pending

Successful endpoint fetches are saved in this browser's local storage and merged
with backend results when Pending loads or refreshes. Empty or unavailable backend
results do not erase local cards. Re-fetching the same article does not duplicate
it, while different lesson days are retained. Local shared-card history is also
restored on reload. Other open tabs receive storage updates. This is device-local
storage, not account synchronization; clearing browser site data removes these
cards. If storage is unavailable, the app warns that cards are session-only.

The persistent session uses the provider's refresh-token expiry, rather than an
unbounded browser login. Restoring a still-valid access token does not contact
the provider. Expired access tokens are renewed server-side. Temporary provider
failures preserve the refresh cookie and show a retry message. A rejected refresh
clears the session and starts a new login. No refresh tokens are exposed to
frontend JavaScript or stored in localStorage. A new connection is needed once
after upgrading from the old in-memory-only implementation.

### Chosun Daily test endpoint

In API endpoint registration, use **조선일보 테스트 엔드포인트 채우기** and register
`GET https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10`
as a generic JSON API. Fetch imports up to ten articles as individual local Pending
messages. Publisher URLs deduplicate repeat imports and preserve shared messages.
The preset leaves scheduling disabled. Registered endpoints and imported messages
are stored in this browser, rather than Firestore.

The frontend uses `GET /api/v1/integrations/chosun-daily/articles` on Moatok's backend
to avoid upstream CORS restrictions. This public read-only proxy uses a fixed upstream
URL, permits no redirects, caps responses at 2 MiB, and returns 502 on upstream failure.
