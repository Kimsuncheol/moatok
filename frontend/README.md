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
│   ├── icon-192.svg          # 192x192 PWA maskable icon
│   ├── icon-512.svg          # 512x512 PWA maskable icon
│   └── manifest.webmanifest  # PWA manifest
├── src/
│   ├── App.vue               # Root application shell with AppHeader and BottomNav
│   ├── main.ts               # Vue application entrypoint (Pinia, Router)
│   ├── env.d.ts              # Vite & window.Kakao type definitions
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
│   │   └── NotificationBanner.vue # Permission prompt for FCM notifications
│   └── views/
│       ├── PendingView.vue   # Active pending briefings list
│       ├── HistoryView.vue   # Shared briefings history archive
│       ├── SettingsView.vue  # Appearance, notifications & sharing policy
│       └── MessageDetailView.vue # Focused single-briefing detail view
└── tests/
    ├── AppearanceToggle.spec.ts # Segmented control & no-dropdown verification
    ├── BottomNav.spec.ts        # Navigation tabs & badge count tests
    ├── kakaoService.spec.ts     # User-initiated Kakao sharing & fallback tests
    ├── messagesStore.spec.ts    # Pinia messages state & markAsShared tests
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
| `VITE_FIREBASE_API_KEY` | Firebase Web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase Authentication domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase / Google Cloud project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | FCM Messaging sender ID |
| `VITE_FIREBASE_APP_ID` | Firebase Web App ID |
| `VITE_FIREBASE_VAPID_KEY` | FCM Web Push Certificate (VAPID key) |
| `VITE_KAKAO_JAVASCRIPT_KEY` | *(Optional)* Kakao Developers JavaScript SDK key for `Kakao.Share` |

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

Runs all 13 unit & component tests across AppearanceToggle, BottomNav, stores, and Kakao sharing:

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
