# Moatok Mobile-First Vue 3 PWA (카카오톡 공유 비서)

A mobile-first, high-contrast monochrome **Vue 3 Progressive Web Application (PWA)** that allows users to review curated content briefings and initiate KakaoTalk sharing.

Pairs with the separate Python **Flask REST API** (`app/`) and **Cloud Firestore** backend.

---

## Architectural Boundary & KakaoTalk Sharing Model

> **CRITICAL ARCHITECTURAL BOUNDARY**:
> **This application DOES NOT automatically post messages to KakaoTalk Open Chat rooms or personal chats on a user's behalf.**

### Why User-Initiated Sharing?
1. **Kakao Platform Policies**: Automatic or headless message posting to Open Chat rooms without user presence violates Kakao terms of service and can result in immediate account/API suspension.
2. **User Agency & Destination Control**: The user must review the drafted briefing and **explicitly choose the destination chatroom or friend** within KakaoTalk.
3. **Clean Division of Responsibility**:
   - **Python Flask Backend**: Collects RSS/API feeds, formats briefings with length limits, deduplicates in Firestore, and sends push notifications via Firebase Cloud Messaging (FCM).
   - **Vue 3 PWA**: Receives push notifications, provides a fast monochrome mobile review interface, and launches the Kakao Share picker or Web Share sheet.
   - **KakaoTalk App**: User selects the target Open Chat room or conversation to dispatch the message.

---

## Design System & Features

- **Monochrome Mobile-First Design**: Clean, high-contrast, distraction-free aesthetic with subtle borders, system fonts, and zero extraneous colors. Max container width: 480px (optimized for mobile screens).
- **Appearance Modes**:
  - `System`: Automatically synchronizes with OS preference (`prefers-color-scheme: dark`).
  - `Light`: Crisp monochrome light palette.
  - `Dark`: Deep OLED-friendly true black palette.
  - **No Dropdowns**: Uses a responsive 3-way segmented control (`AppearanceToggle.vue`).
- **Bottom Navigation Bar**: Fixed bottom bar with safe-area padding for mobile home indicators:
  - **Pending** (`/`): Awaiting review and user-initiated KakaoTalk sharing (with pending badge count).
  - **History** (`/history`): Archive of previously shared briefings.
  - **Settings** (`/settings`): Appearance mode toggle, FCM push permissions, Firebase user status, and backend connectivity.
- **PWA Capabilities**: Service worker caching, Web App Manifest (`manifest.webmanifest`), mobile standalone display, and installability.

---

## Tech Stack

- **Framework**: Vue 3 (Composition API `<script setup lang="ts">`)
- **Language**: TypeScript 5.6
- **Build Tool**: Vite 5 + `vite-plugin-pwa`
- **Routing**: Vue Router 4
- **State Management**: Pinia 2
- **Authentication**: Firebase Authentication (ID token Bearer header propagation to Flask API)
- **Push Notifications**: Firebase Cloud Messaging (FCM Web Push)
- **Unit Testing**: Vitest 2 + `@vue/test-utils` + JSDOM

---

## Project Structure

```text
frontend/
├── .env.example              # Client-side environment variables template
├── .gitignore                # Git ignore rules for node_modules, dist, etc.
├── index.html                # PWA entrypoint with mobile viewport & Kakao JS SDK
├── package.json              # NPM dependencies & scripts
├── postcss.config.js         # PostCSS configuration
├── tsconfig.json             # TypeScript compiler settings
├── tsconfig.node.json        # TypeScript configuration for Vite/Vitest
├── vite.config.ts            # Vite bundler, PWA plugin & API proxy
├── vitest.config.ts          # Vitest testing configuration
├── public/
│   ├── favicon.svg           # Monochrome SVG favicon
│   ├── favicon.png           # 32x32 local PNG favicon
│   ├── icon-192.svg          # 192x192 PWA vector icon
│   ├── icon-512.svg          # 512x512 PWA vector icon
│   ├── pwa-192x192.png       # 192x192 local PNG PWA icon (maskable & any)
│   ├── pwa-512x512.png       # 512x512 local PNG PWA icon (maskable & any)
│   ├── apple-touch-icon.png  # 180x180 Apple touch icon for iOS Home Screen
│   └── manifest.webmanifest  # PWA manifest
├── src/
│   ├── App.vue               # Root application shell with AppHeader, BottomNav & ReloadPrompt
│   ├── main.ts               # Vue application entrypoint (Pinia, Router)
│   ├── env.d.ts              # Vite, window.Kakao & virtual:pwa-register type definitions
│   ├── assets/
│   │   └── main.css          # Monochrome design tokens & light/dark CSS variables
│   ├── types/
│   │   └── index.ts          # ShareMessage, AppearanceMode, UserProfile interfaces
│   ├── router/
│   │   └── index.ts          # Routes: /, /history, /settings, /messages/:id
│   ├── services/
│   │   ├── api.ts            # Flask REST API client with Firebase Bearer auth
│   │   ├── firebase.ts       # Firebase app, auth & messaging initialization
│   │   └── kakao.ts          # Kakao Share SDK, Web Share API & clipboard fallbacks
│   ├── stores/
│   │   ├── auth.ts           # Firebase user authentication state
│   │   ├── messages.ts       # Pending & History briefings store
│   │   ├── notifications.ts  # FCM device registration & foreground message listener
│   │   └── theme.ts          # System, light & dark appearance store
│   ├── components/
│   │   ├── AppHeader.vue     # Sticky mobile top bar with brand & sync button
│   │   ├── BottomNav.vue     # Bottom navigation (Pending, History, Settings)
│   │   ├── AppearanceToggle.vue # 3-way segmented control (NO dropdown)
│   │   ├── MessageCard.vue   # Briefing item card with status badge & actions
│   │   ├── ShareModal.vue    # Full briefing review & KakaoTalk sharing sheet
│   │   ├── NotificationBanner.vue # Permission prompt for FCM notifications
│   │   └── ReloadPrompt.vue  # PWA service worker update prompt banner
│   └── views/
│       ├── PendingView.vue   # Active pending briefings list
│       ├── HistoryView.vue   # Shared briefings history archive
│       ├── SettingsView.vue  # Appearance, notifications & sharing policy
│       └── MessageDetailView.vue # Focused single-briefing detail view
└── tests/
    ├── AppearanceToggle.spec.ts # Segmented control & no-dropdown verification
    ├── apiClient.spec.ts        # API client, Bearer token injection, retry on 401 & expiration tests
    ├── authStore.spec.ts        # Pinia auth store, sign-in methods, token refresh & state transitions
    ├── BottomNav.spec.ts        # Navigation tabs & badge count tests
    ├── kakaoService.spec.ts     # User-initiated Kakao sharing & fallback tests
    ├── MessageCard.spec.ts      # Card title, source, status, time & selection tests
    ├── MessageDetailView.spec.ts# Message detail page, admin editing & Kakao sharing tests
    ├── messagesStore.spec.ts    # Pinia messages state & markAsShared tests
    ├── PendingView.spec.ts      # Pending page loading, empty, error, pull-to-refresh & navigation
    ├── pwaManifest.spec.ts      # Web App Manifest & icon presence verification
    ├── ReloadPrompt.spec.ts     # PWA update prompt & reload action tests
    ├── ShareModal.spec.ts       # Disclaimer banner & share event tests
    └── themeStore.spec.ts       # System/Light/Dark persistence tests
```

---

## Environment Configuration

Copy `.env.example` to `.env` in the `frontend` folder:

```bash
cp frontend/.env.example frontend/.env
```

| Variable | Description |
| :--- | :--- |
| `VITE_API_BASE_URL` | Base URL of the Python Flask REST API (e.g., `http://localhost:8080`) |
| `VITE_FIREBASE_AUTH_SIGN_IN_METHOD` | Configurable preferred sign-in method (`email`, `anonymous`, `google`, default: `email`) |
| `VITE_FIREBASE_API_KEY` | Firebase Web API key (Public client config ONLY) |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase Authentication domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase / Google Cloud project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | FCM Messaging sender ID |
| `VITE_FIREBASE_APP_ID` | Firebase Web App ID |
| `VITE_FIREBASE_VAPID_KEY` | FCM Web Push Certificate (VAPID key) |
| `VITE_KAKAO_JAVASCRIPT_KEY` | *(Optional)* Kakao Developers JavaScript SDK key for `Kakao.Share` |

> [!CAUTION]
> **No Secrets or Service Account Keys in Frontend**:
> The frontend bundles only public Firebase client web configuration. **Never** include Google Cloud service account JSON keys, Kakao Client Secrets, or Cloud Scheduler credentials in the frontend repository or environment variables.

---

## Firebase Authentication & Backend REST API Integration

### 1. Configurable Sign-in Methods
Moatok supports multiple sign-in providers configured via `VITE_FIREBASE_AUTH_SIGN_IN_METHOD`:
- **Email / Password** (`loginWithEmail`, `signupWithEmail`): Supports standard user authentication and account creation with localized error messages.
- **Anonymous / Guest** (`loginAsGuest`): Instant sign-in without registration for reviewing briefings and sharing.
- **Google Sign-In** (`loginWithGoogle`): OAuth pop-up authentication via `GoogleAuthProvider`.
- **Polymorphic Dispatcher** (`signIn({ method, ... })`): Dispatches dynamically to the chosen method.

### 2. Pinia Authentication State Management (`useAuthStore`)
Manages reactive states:
- `user`: Firebase `User` instance.
- `profile`: Verified user profile retrieved from Flask backend (`/api/v1/auth/me`).
- `status`: `'loading' | 'authenticated' | 'signed_out' | 'expired' | 'error'`.
- `isAdmin`: Computed property verifying server-validated Firebase custom claims (`admin: true`).

### 3. Bearer Token Propagation & Reactive 401 Session Refresh
- Every call made by `api.ts` automatically attaches an `Authorization: Bearer <ID_TOKEN>` header resolved from `authStore.getIdToken()`.
- **Automatic Token Refresh on 401**: When an API call returns `401 Unauthorized` with `code: "token_expired"`:
  1. `api.ts` automatically calls `tokenProvider(true)` to force-refresh the Firebase ID token using the user's refresh token.
  2. The request is retried **once** with the newly minted token.
  3. If the retry fails or the session is revoked, `onSessionExpired` triggers `authStore.handleSessionExpired()`, setting `status: 'expired'` and notifying the user to sign in again.

---

## PWA Installation & Platform Instructions (Android & iOS)

### Android (Chrome / Samsung Internet)
1. Open the web app in Chrome or Samsung Internet.
2. An automatic install banner will appear, or tap the three dots menu (**⋮**) in the upper right/lower corner.
3. Tap **"Install app"** or **"Add to Home screen"** (**앱 설치** / **홈 화면에 추가**).
4. The PWA will be installed as an independent standalone app in your app drawer and home screen.

### iOS / iPadOS (Safari)
> **IMPORTANT: iOS Version & Home Screen Requirements**
>
> 1. **iOS 16.4+ Required for Web Push**: Apple introduced Web Push Notification support for PWAs in iOS / iPadOS 16.4. Older iOS versions cannot receive web push notifications.
> 2. **Must Be Launched from Home Screen**: Web Push notifications (`Notification.requestPermission()`) and standalone full-screen execution **only function after adding the PWA to the Home Screen**. In regular Safari browser tabs, Web Push is disabled by Apple policy.

**Step-by-Step iOS Installation**:
1. Open the web app in **Safari** (third-party in-app browsers like KakaoTalk or Instagram in-app browser do not support PWA installation).
2. Tap the **Share icon** (square with an arrow pointing upward) in the Safari bottom toolbar.
3. Scroll down and tap **"Add to Home Screen"** (**홈 화면에 추가**).
4. Tap **"Add"** in the top right corner.
5. Exit Safari and launch **Moatok** from the newly created Home Screen icon.
6. In **Settings** (`/settings`), tap **"푸시 알림 권한 허용하기"** to enable push notifications.

---

## Security Context Requirements: HTTPS & Localhost

Progressive Web App features — including **Service Worker registration**, **CacheStorage precaching**, **Web App Manifest installation**, and **Firebase Cloud Messaging Web Push** — strictly require a **Secure Context (HTTPS)** per W3C and browser security standards:

1. **Local Development Exception**:
   - `http://localhost` (e.g. `http://localhost:5173`) and `http://127.0.0.1` are treated as secure contexts by modern browsers.
   - You can test PWA service workers and updates locally without SSL certificates.
2. **Production Deployment Requirement**:
   - Production instances **must be served over HTTPS** with a valid TLS certificate (e.g., Firebase Hosting, Cloud Run with custom domain, Cloudflare, Vercel, Netlify).
   - If deployed on an insecure remote IP or plain HTTP domain (e.g., `http://192.168.x.x:5173` or `http://moatok.example.com`), iOS Safari and Android Chrome will **block** Service Worker registration and Web Push notifications.

---

## Caching Strategy & Security Guarantees

Configured in `vite.config.ts` via `vite-plugin-pwa` and Workbox:

1. **Safe Application Shell Pre-caching**:
   - HTML, CSS, JavaScript chunks, fonts, and icon assets are precached with content hashes (`globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}']`).
   - Uses `cleanupOutdatedCaches: true` to purge stale revisions upon update.
2. **Zero-Cache Policy for Authenticated & Sensitive APIs**:
   - `navigateFallbackDenylist: [/^\/api\//, /^\/health/, /^\/internal\//]`
   - `runtimeCaching: [{ urlPattern: /^\/api\/.*/, handler: 'NetworkOnly' }]`
   - **Guarantees**: Authenticated API responses (user messages, device tokens, Firebase ID tokens, admin endpoints) are **never cached** in the Service Worker or CacheStorage.
3. **PWA Update Prompt**:
   - Configured with `registerType: 'prompt'`.
   - When a new build is deployed, [`ReloadPrompt.vue`](src/components/ReloadPrompt.vue) detects the waiting service worker via `virtual:pwa-register/vue` and displays an unobtrusive monochrome banner asking the user to update.

---

## Official Kakao SDK Integration & Developer Console Settings

The PWA integrates the official **Kakao SDK for JavaScript (v2.7.2)** (`https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js`) for user-directed sharing.

### 1. Kakao Developers Console Settings Guide

To configure Kakao sharing for your deployment:

1. **Create Kakao Developer App**:
   - Navigate to [Kakao Developers Console](https://developers.kakao.com/).
   - Log in and select **[내 애플리케이션] > [애플리케이션 추가하기]**.
   - Fill in the App Name (e.g. `Moatok`) and Company/Developer Name.
2. **Obtain JavaScript Key**:
   - In your application dashboard, go to **[앱 설정] > [요약 정보]**.
   - Copy the **JavaScript 키** (e.g. `1234567890abcdef1234567890abcdef`).
   - Set in `frontend/.env`:
     ```bash
     VITE_KAKAO_JAVASCRIPT_KEY=your_kakao_javascript_key_here
     ```
3. **Web Platform & Site Domain Registration (CRITICAL: KOE101 Error Prevention)**:
   - Go to **[앱 설정] > [플랫폼] > [Web 플랫폼 등록]**.
   - Register all web domains hosting this application:
     - Local development: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:8080`
     - Production deployment: `https://moatok.example.com`, `https://<your-project-id>.web.app`
   - Up to 10 web site domains can be registered per Kakao app.

> [!IMPORTANT]
> **Domain Validation & External Article Routing (KOE101)**:
> The official Kakao SDK strictly validates that all link parameters (`mobileWebUrl`, `webUrl`) in `Kakao.Share.sendDefault` belong to domains registered in your Kakao Developers Console. Attempting to pass external article URLs (e.g. `https://techcrunch.com/...`) directly into Kakao template link properties triggers a Kakao server validation failure: `KOE101 (Unregistered domain)`.
>
> **Moatok Architectural Design**:
> - Template link properties (`webUrl`, `mobileWebUrl`) point to the application's registered domain detail route: `${window.location.origin}/messages/${message.id}`.
> - When recipients click the KakaoTalk card, they open the detail page on the registered domain.
> - The detail page displays the full briefing and provides the direct clickable link (`message.target_url`) to the original article source.

### 2. Supported Message Templates

Moatok leverages the official Kakao default templates via `Kakao.Share.sendDefault`:
- **Feed Template (`feed`)**: Used when the content briefing contains an image (`imageUrl`). Includes article title, briefing excerpt/description, hero image, and action button (`자세히 보기` / `브리핑 상세 보기`).
- **Text Template (`text`)**: Used when no image is available. Displays structured briefing text, domain link, and action button (`브리핑 상세 보기`).

### 3. Graceful Fallback Strategy

When Kakao SDK sharing cannot proceed (e.g., ad blockers, missing app key, network failure, or desktop browser):
1. **Web Share API (`navigator.share`)**: Opens the native mobile operating system share sheet, enabling the user to choose KakaoTalk or any messaging app.
2. **Clipboard Copy (`navigator.clipboard.writeText`)**: Automatically copies the formatted briefing text and prompts the user with clear instructions to paste into KakaoTalk.

### 4. Share Initiation Telemetry vs Delivery Decoupling

> [!WARNING]
> **Clicking the Share Button DOES NOT Prove Successful Delivery**:
> - Clicking `카카오톡으로 공유하기` only initiates the share flow and launches the KakaoTalk selector.
> - The application reports share initiation to the Flask backend (`POST /api/v1/messages/<id>/share-attempt`) for observability.
> - This telemetry does **not** change message status to `shared` and does not set `kakao_shared: true`.
> - The user must select the recipient in KakaoTalk and send the message, then explicitly confirm via `카카오톡 전송 완료로 기록하기` (`POST /api/v1/messages/<id>/mark-shared`).

### 5. Real-Device Open Chat Testing Requirement

> [!NOTE]
> **Open Chat Room Selection Availability**:
> Kakao Open Chat rooms can only be selected as a sharing destination via the native KakaoTalk mobile app on **actual physical mobile devices (Android or iOS)** with KakaoTalk installed.
> - Desktop web browsers, headless automation, and mobile simulators cannot verify or select Open Chat rooms via Kakao Share.
> - All Open Chat sharing workflows must be validated on physical Android/iOS hardware.

### 6. Strict Prohibition of Private Protocols and Automation

> [!CAUTION]
> - **No Private Protocols**: Never use undocumented or reverse-engineered internal KakaoTalk schemes (`kakaotalk://` RPCs).
> - **No Background Automation**: Never use background UI automation, accessibility services, or bot frameworks to bypass the KakaoTalk user interface.
> - Moatok strictly complies with Kakao's official developer terms of service and user privacy guidelines.

---

## Local Development & Testing Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Run Development Server

```bash
npm run dev
```
Open `http://localhost:5173` in your browser or mobile emulator. Vite proxies `/api` and `/health` requests to the Flask backend running on `http://localhost:8080`.

### 3. Run Automated Frontend Tests

Runs all 53 unit & component tests across AppearanceToggle, apiClient, authStore, BottomNav, MessageCard, MessageDetailView, PendingView, stores, Kakao sharing, PWA manifest, and ReloadPrompt:

```bash
npm test
```

### 4. Build for Production

Performs TypeScript type-checking via `vue-tsc` and bundles the PWA into `frontend/dist/`:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```
