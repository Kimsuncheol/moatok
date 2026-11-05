# Firebase Hosting Deployment Guide & Real-Device Test Checklist

This guide covers deploying the **Moatok Vue 3 Progressive Web Application (PWA)** (`frontend/`) to **Firebase Hosting**, configuring SPA routing and caching, setting up Kakao Developers and Firebase Authentication authorized domains, and executing the mandatory real-device test checklist on Android and iOS.

---

## 1. Prerequisites

Before deploying to Firebase Hosting:
1. **Google Cloud / Firebase Project**: A Firebase-enabled Google Cloud project with:
   - **Firebase Hosting** enabled.
   - **Firebase Authentication** configured.
   - **Cloud Firestore** and **Firebase Cloud Messaging (FCM)** enabled.
2. **Cloud Run Backend**: The Flask REST API (`app/`) deployed to Google Cloud Run (see [DEPLOYMENT.md](DEPLOYMENT.md)).
3. **Kakao Developers App**: An application created in [Kakao Developers Console](https://developers.kakao.com) with a valid JavaScript App Key.
4. **Tools Installed**:
   - Node.js (v20+) and npm.
   - Firebase CLI: `npm install -g firebase-tools` (or run via `npx firebase-tools`).

---

## 2. Production Environment Configuration

In `frontend/`, create `.env.production` from the template `.env.production.example`:

```bash
cd frontend
cp .env.production.example .env.production
```

Configure the environment variables in `frontend/.env.production`:

```bash
# 1. Backend REST API URL
# Option A: Direct Cloud Run URL (recommended when CORS is configured for Firebase Hosting)
VITE_API_BASE_URL=https://moatok-backend-your-project-id.asia-northeast3.run.app
# Option B: Leave empty or omit if using same-origin Firebase Hosting rewrites (see Section 3.2)
# VITE_API_BASE_URL=

# 2. Configurable Preferred Sign-in Method (email, anonymous, google)
VITE_FIREBASE_AUTH_SIGN_IN_METHOD=email

# 3. Firebase Client Web Configuration (Public client identifiers ONLY)
# SECURITY NOTICE: Never place Google Cloud service account keys, private keys,
# or Kakao client secrets here. Only public web client configuration is permitted.
VITE_FIREBASE_API_KEY=AIzaSyProductionKeyExample123456789
VITE_FIREBASE_AUTH_DOMAIN=your-gcp-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-gcp-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-gcp-project-id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789012
VITE_FIREBASE_APP_ID=1:123456789012:web:abcdef1234567890
VITE_FIREBASE_VAPID_KEY=BExampleVAPIDPublicKey1234567890abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ

# 4. Kakao Developers JavaScript App Key
# Obtain from Kakao Developers Console ([앱 설정] > [요약 정보] > [JavaScript 키])
VITE_KAKAO_JAVASCRIPT_KEY=your-production-kakao-javascript-key
```

> [!CAUTION]
> **Credential Hygiene**: Never place Google Cloud service account keys, private keys, admin secrets, or Kakao REST API keys in frontend environment files or client-side bundles. Only public client configuration keys (`VITE_FIREBASE_API_KEY`, `VITE_KAKAO_JAVASCRIPT_KEY`, etc.) belong in the frontend.

---

## 3. Firebase Hosting & SPA Route Fallback Configuration

The project root contains [`firebase.json`](firebase.json) and [`.firebaserc`](.firebaserc).

### 3.1 SPA Routing Fallback (`rewrites`)
A Single Page Application (SPA) uses client-side routing (Vue Router in HTML5 history mode). When a user navigates to `/`, `/history`, `/settings`, or deep-links directly to `/messages/:id`, or presses browser refresh:
- Without an SPA rewrite, the static hosting CDN searches for a physical `/messages/:id/index.html` file and returns an HTTP `404 Not Found`.
- With the rewrite rule below, Firebase Hosting serves `/index.html` for all non-static asset routes, allowing Vue Router to resolve the route on the client.

```json
{
  "hosting": {
    "public": "frontend/dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "/sw.js",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache, no-store, must-revalidate"
          },
          {
            "key": "Service-Worker-Allowed",
            "value": "/"
          }
        ]
      },
      {
        "source": "/manifest.webmanifest",
        "headers": [
          {
            "key": "Content-Type",
            "value": "application/manifest+json; charset=utf-8"
          },
          {
            "key": "Cache-Control",
            "value": "no-cache"
          }
        ]
      },
      {
        "source": "/assets/**",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        "source": "**",
        "headers": [
          {
            "key": "X-Content-Type-Options",
            "value": "nosniff"
          },
          {
            "key": "X-Frame-Options",
            "value": "DENY"
          },
          {
            "key": "Referrer-Policy",
            "value": "strict-origin-when-cross-origin"
          }
        ]
      }
    ]
  }
}
```

### 3.2 Cache-Control Policy for PWAs
- **/sw.js (Service Worker)**: Must **never** be cached (`no-cache, no-store, must-revalidate`). If cached by the CDN or browser, client devices may run stale versions indefinitely and fail to pick up critical PWA updates.
- **/manifest.webmanifest**: Served with `Content-Type: application/manifest+json` and `Cache-Control: no-cache` to ensure browser install prompts receive up-to-date icons and theme colors.
- **/assets/\*\***: Static JavaScript chunks and CSS bundles are generated with Vite content hashes (e.g. `index-C1iqHc1Z.js`). They are safely cached with `public, max-age=31536000, immutable`.
- **Security Headers**: All routes receive `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`.

### 3.3 Optional: Same-Origin Cloud Run Rewrites
If you prefer not to manage Cross-Origin Resource Sharing (CORS) between Firebase Hosting and Cloud Run, you can proxy `/api/**` calls directly to Cloud Run through Firebase Hosting by updating `firebase.json`:

```json
{
  "hosting": {
    "public": "frontend/dist",
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "moatok-backend",
          "region": "asia-northeast3"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```
When using this rewrite, set `VITE_API_BASE_URL=` (empty string) in `frontend/.env.production` so API requests target the same origin (`/api/...`).

---

## 4. Production Build & Deployment Commands

### 4.1 Set Firebase Project Alias
Edit [`.firebaserc`](.firebaserc) with your actual Google Cloud / Firebase project ID:
```json
{
  "projects": {
    "default": "your-gcp-project-id"
  }
}
```
Or via CLI:
```bash
firebase use --add your-gcp-project-id
```

### 4.2 Build Frontend for Production
Run the production build script which performs strict TypeScript type-checking (`vue-tsc --noEmit`) and Vite bundling with Workbox service worker generation:

```bash
# Option A: From root directory
npm run build:prod

# Option B: From frontend directory
cd frontend
npm run build
```

Verify that `frontend/dist/` contains:
- `index.html`
- `sw.js` and `workbox-*.js`
- `manifest.webmanifest`
- `assets/` (hashed `.js` and `.css` files)
- Icons: `pwa-192x192.png`, `pwa-512x512.png`, `apple-touch-icon.png`, `favicon.png`, `favicon.svg`

### 4.3 Deploy to Firebase Hosting
Deploy only the hosting target:

```bash
# Option A: From root directory
npm run deploy:hosting

# Option B: Direct Firebase CLI command
firebase deploy --only hosting
```

Upon completion, Firebase CLI will output your live hosting URLs:
- `https://your-gcp-project-id.web.app`
- `https://your-gcp-project-id.firebaseapp.com`

---

## 5. Kakao Developers Console Domain Registration (`KOE101` Prevention)

The official Kakao SDK strictly validates that all link targets (`mobileWebUrl`, `webUrl`) in `Kakao.Share.sendDefault` belong to domains registered in your Kakao Developers Console. Attempting to share without registering your deployed domain triggers a Kakao server error: `KOE101 (Unregistered domain)`.

### Registration Steps:
1. Navigate to the [Kakao Developers Console](https://developers.kakao.com).
2. Log in and select your application under **[내 애플리케이션]**.
3. In the left navigation sidebar, navigate to **[앱 설정] > [플랫폼]**.
4. Scroll to the **[Web]** platform section and click **[등록]** (or **[수정]** if already created).
5. In the **[사이트 도메인]** field, register all production and development domains (one per line, up to 10 domains):
   ```text
   https://your-gcp-project-id.web.app
   https://your-gcp-project-id.firebaseapp.com
   https://moatok.example.com
   http://localhost:5173
   http://127.0.0.1:5173
   ```
6. Click **[저장]**.

### How Moatok Respects Kakao Link Policies
- When generating Kakao Share cards (`src/services/kakao.ts`), Moatok sets `webUrl` and `mobileWebUrl` to the registered PWA detail route: `${window.location.origin}/messages/${message.id}`.
- When recipients tap the KakaoTalk card, they open the briefing detail page on the registered domain.
- The detail page renders the full content and provides a direct, verified link to the original article source (`target_url`).

---

## 6. Firebase Authentication Authorized Domains

Firebase Authentication restricts OAuth popup/redirect operations and token exchanges to approved origin domains to prevent malicious cross-site token interception.

### Registration Steps:
1. Open the [Firebase Console](https://console.firebase.google.com).
2. Select your project and navigate to **[Authentication]** > **[Settings] (설정)** tab.
3. Select **[Authorized domains] (승인된 도메인)**.
4. Verify the default entries:
   - `localhost`
   - `your-gcp-project-id.firebaseapp.com`
   - `your-gcp-project-id.web.app`
5. If using a custom domain (e.g., `moatok.example.com`), click **[도메인 추가 (Add domain)]**, enter your custom domain, and save.
6. If using Google Sign-in, also ensure the OAuth 2.0 Web Client ID in Google Cloud Console has these domains added under **Authorized JavaScript origins** and **Authorized redirect URIs**.

---

## 7. Real-Device Test Checklist (Android & iOS)

Execute this comprehensive 8-step test checklist on physical hardware (Android phone with Chrome and iPhone with Safari / iOS 16.4+) after deploying to Firebase Hosting.

```
================================================================================
           MOATOK PWA REAL-DEVICE VERIFICATION CHECKLIST (Android & iOS)
================================================================================
```

### [ ] Step 1: Open Deployed PWA Over HTTPS
- **Target URL**: `https://<your-gcp-project-id>.web.app`
- **Actions**:
  1. Open the URL in mobile Chrome (Android) or mobile Safari (iOS).
  2. Verify the browser shows a valid SSL/TLS certificate (padlock icon).
  3. Verify the monochrome layout fits the mobile viewport (max width 480px, responsive centering).
  4. Verify the bottom navigation bar (`Pending`, `History`, `Settings`) is visible with safe-area bottom padding.
  5. Toggle Appearance modes (`System`, `Light`, `Dark`) in `Settings` and confirm instant palette switching with zero dropdown widgets.
- **Pass Criteria**: Clean render, valid HTTPS, responsive mobile layout, correct monochrome styling.

---

### [ ] Step 2: Add PWA to Home Screen
- **Android (Chrome)**:
  1. Tap the Chrome three-dot menu (or tap the "앱 설치" / install banner if prompted).
  2. Select **[홈 화면에 추가]** / **[앱 설치]**.
  3. Confirm the app title is "모아톡" and icon displays properly (`pwa-192x192.png`).
  4. Launch Moatok from the Home Screen.
  5. Verify the app runs in **standalone mode** (no browser address bar or bottom browser controls).
- **iOS (Safari - iOS 16.4+)**:
  1. Tap the Safari **Share** button (box with upward arrow).
  2. Scroll down and select **[홈 화면에 추가 (Add to Home Screen)]**.
  3. Confirm the touch icon (`apple-touch-icon.png`) and title "모아톡".
  4. Tap **[추가 (Add)]**.
  5. Launch Moatok from the iOS Home Screen.
  6. Verify the app launches as an independent Web Clip with standalone display mode and no Safari navigation bar.
- **Pass Criteria**: Icon added to Home Screen; launches in standalone fullscreen mode on both platforms.

---

### [ ] Step 3: Sign In
- **Actions**:
  1. Navigate to `Settings` tab or tap the sign-in prompt.
  2. Sign in using the method configured in `VITE_FIREBASE_AUTH_SIGN_IN_METHOD` (Email/password, Google Sign-in, or Anonymous guest).
  3. Verify sign-in state transitions to signed-in.
  4. Inspect network requests via remote debugging: verify that API calls to `/api/v1/messages` include the header:
     `Authorization: Bearer <firebase_id_token>`
  5. Test session persistence: close and re-launch the standalone PWA; verify the user remains authenticated via Pinia `authStore`.
- **Pass Criteria**: Successful sign-in, valid Firebase ID token attached to API requests, session maintained across app relaunches.

---

### [ ] Step 4: Receive a Test Push Notification Where Supported
- **Android**:
  1. On the home page or in `Settings`, tap **[알림 켜기]** / **[알림 권한 요청]**.
  2. Accept the browser permission dialog.
  3. Confirm the device registers its FCM token at `POST /api/v1/devices/fcm-token`.
  4. Trigger a test push notification from the backend or Cloud Scheduler collection job.
  5. **Foreground test**: Verify the in-app notification banner or toast appears.
  6. **Background test**: Send app to background or lock device; verify system notification tray displays the brief message.
- **iOS (iOS 16.4+ Home Screen Requirement)**:
  1. > [!IMPORTANT]
     > **iOS Push Limitation**: Web Push API (`PushManager`) is **strictly unavailable** in regular iOS Safari browser tabs. It is **only available** when the PWA is added to the Home Screen and launched as a standalone Web Clip on iOS 16.4 or later.
  2. Launch the standalone Moatok app from the iOS Home Screen.
  3. In `Settings`, tap **[알림 켜기]**.
  4. Accept the iOS system notification prompt.
  5. Verify the device registers its token via `POST /api/v1/devices/fcm-token`.
  6. Lock the device and dispatch a test notification; verify notification appears on the iOS Lock Screen and Notification Center.
- **Pass Criteria**: Push permission granted, FCM token registered, push notification delivered on Android and iOS (Home Screen PWA).

---

### [ ] Step 5: Open a Share Message
- **Actions**:
  1. Tap an incoming push notification or tap an item on the `Pending` tab (`/`).
  2. Verify navigation to the detail view (`/messages/:id`).
  3. **SPA Fallback Verification**: Press the browser reload button or refresh gesture on `/messages/:id`. Confirm the page reloads cleanly and does **not** return a 404 error from Firebase Hosting.
  4. Verify the detail view presents:
     - Article title
     - Formatted share text (`formatted_text`)
     - Source name (e.g. RSS feed name)
     - Original article URL (`target_url`) with a working link
     - UTC creation time formatted to local time
     - Current share status (`대기 중` / `pending`)
  5. (Admin account only): Verify the edit text action functions and saves via `PATCH /api/v1/admin/share-messages/:id`.
- **Pass Criteria**: Route loads reliably (including on refresh), all fields display clearly, original link works.

---

### [ ] Step 6: Launch KakaoTalk Sharing
- **Actions**:
  1. On the message detail page, tap the prominent **[카카오톡으로 공유하기]** button.
  2. Verify the Kakao SDK initializes without error:
     - Confirm no `KOE101` error occurs (domain is correctly registered in Kakao Developers Console).
     - Confirm no console error about uninitialized Kakao SDK.
  3. Confirm the native KakaoTalk application opens.
  4. (Fallback verification): In an environment without native KakaoTalk (e.g. desktop simulator), confirm the app gracefully falls back to the native Web Share API (`navigator.share`) or copies the text to the clipboard with user feedback.
- **Pass Criteria**: Tapping the button launches KakaoTalk on mobile without domain errors (`KOE101`); fallback activates when SDK is unavailable.

---

### [ ] Step 7: Check Open Chat Room Selection in KakaoTalk
- **Actions**:
  1. In the KakaoTalk sharing screen that opens, examine the recipient picker.
  2. Select an **Open Chat room** (오픈채팅방), group chat, or 1:1 conversation as the target.
  3. Send the message.
  4. Open the chosen Open Chat room in KakaoTalk:
     - Verify the message card contains the article title, summary description, and action button (`브리핑 상세 보기`).
     - Tap `브리핑 상세 보기`: verify it opens the deployed PWA detail page (`https://<project-id>.web.app/messages/:id`).
     - From that page, verify the user can click through to the original publisher URL.
- **Important Note**:
  > [!NOTE]
  > Kakao Open Chat room availability **cannot be checked or automated via desktop web, emulators, or bot scripts**. Physical device testing with the official KakaoTalk client is required.
- **Pass Criteria**: Open Chat room is selectable in KakaoTalk; shared card renders properly; link navigates to the PWA detail view.

---

### [ ] Step 8: Confirm Delivery Information Received by Backend
- **Actions**:
  1. **Share Attempt Telemetry**:
     - When the user clicked **[카카오톡으로 공유하기]** in Step 6, the PWA called `POST /api/v1/messages/:id/share-attempt`.
     - In Firestore, inspect `share_messages/<id>`: verify `share_attempt_count >= 1` and `last_share_attempt_at` is updated.
     - Verify `status` **remains** `"pending"` and `kakao_shared` **remains** `false` (clicking the share button does not claim delivery).
  2. **User Confirmation**:
     - After sending in KakaoTalk, return to the PWA.
     - Tap **[카카오톡 전송 완료로 기록하기]** (or confirmation prompt).
     - The PWA calls `POST /api/v1/messages/:id/mark-shared` with `share_channel: "kakaotalk_web_sdk"`.
     - Inspect Firestore: verify `status: "shared"`, `kakao_shared: true`, `shared_by_user_id: "<uid>"`, and `shared_by_user_at: "<timestamp>"`.
  3. **History Verification**:
     - Navigate to the `History` tab (`/history`).
     - Verify the briefing now appears in History, marked as shared with the recorded attempt count and confirmation timestamp.
- **Pass Criteria**: Telemetry accurately tracks share attempts; delivery confirmation is strictly decoupled from the share button click; Firestore records correct state; History displays verified events.

---

## 8. Troubleshooting & FAQ

| Issue | Cause | Resolution |
|---|---|---|
| **`KOE101` Error** on Kakao Share | Hosting domain not registered in Kakao Console | Add `https://<project-id>.web.app` and `https://<project-id>.firebaseapp.com` to **[Kakao Developers] > [플랫폼] > [Web] > [사이트 도메인]**. |
| **`auth/unauthorized-domain`** | Custom domain not registered in Firebase Auth | Add domain to **[Firebase Console] > [Authentication] > [Settings] > [Authorized domains]**. |
| **404 Not Found** on Page Refresh | Missing SPA rewrite rule | Ensure `firebase.json` has `rewrites: [{"source": "**", "destination": "/index.html"}]`. |
| **PWA Updates Not Appearing** | `/sw.js` cached by browser/CDN | Ensure `firebase.json` headers enforce `Cache-Control: no-cache, no-store, must-revalidate` for `/sw.js`. |
| **iOS Push Notifications Disabled** | Running inside regular Safari tab | iOS requires the PWA to be **Added to Home Screen** on iOS 16.4+ to support Web Push notifications. |
| **CORS Error** on API Requests | Backend not allowing Hosting origin | Update Cloud Run `CORS_ALLOWED_ORIGINS` to include `https://<project-id>.web.app`, or use same-origin rewrites in `firebase.json`. |
