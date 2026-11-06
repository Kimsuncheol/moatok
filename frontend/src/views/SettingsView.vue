<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { connectMyChat, disconnectMyChat } from '@/services/kakaoMyChat'
const kakaoBusy = ref(false)
const kakaoFeedback = ref('')
async function manageKakao(disconnect = false) {
  kakaoBusy.value = true
  try {
    if (disconnect) await disconnectMyChat()
    else await connectMyChat()
    kakaoFeedback.value = disconnect ? '카카오 연결을 해제했습니다.' : '카카오 연결이 유지됩니다. 새로고침 후에도 복원할 수 있습니다.'
  } catch (error) { kakaoFeedback.value = error instanceof Error ? error.message : '카카오 연결에 실패했습니다.' }
  finally { kakaoBusy.value = false }
}

import { useRouter } from 'vue-router'
import { getApiBaseUrl } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useEndpointsStore } from '@/stores/endpoints'
import type { AppearanceMode, AuthSignInMethod } from '@/types'

const router = useRouter()
const endpointsStore = useEndpointsStore()
const notifStore = useNotificationsStore()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const backendStatus = ref<'checking' | 'healthy' | 'unreachable'>('checking')
const isRequestingNotif = ref(false)
const notifFeedback = ref<string | null>(null)

// Platform detection for PWA guidance
const detectedPlatform = computed<'android' | 'ios' | 'desktop'>(() => {
  if (typeof navigator === 'undefined') return 'desktop'
  const ua = navigator.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
    return 'ios'
  }
  if (/Android/.test(ua)) {
    return 'android'
  }
  return 'desktop'
})

const activePlatformTab = ref<'android' | 'ios' | 'desktop'>('desktop')

// Authentication form state
const selectedMethod = ref<AuthSignInMethod>(authStore.preferredSignInMethod)
const authEmail = ref('')
const authPassword = ref('')
const authMode = ref<'login' | 'signup'>('login')
const authSubmitting = ref(false)

// Appearance modes list
interface AppearanceOption {
  mode: AppearanceMode
  name: string
  desc: string
  icon: string
}

const appearanceOptions: AppearanceOption[] = [
  {
    mode: 'system',
    name: '시스템 설정 (System)',
    desc: '기기 운영체제의 다크/라이트 모드 설정에 자동으로 동기화됩니다.',
    icon: '⚙️'
  },
  {
    mode: 'light',
    name: '라이트 모드 (Light)',
    desc: '밝고 선명한 단색 고대비 모노크롬 테마입니다.',
    icon: '☀️'
  },
  {
    mode: 'dark',
    name: '다크 모드 (Dark)',
    desc: '눈의 피로를 줄이고 배터리를 절약하는 트루 블랙 OLED 최적화 테마입니다.',
    icon: '🌙'
  }
]

async function checkBackendHealth() {
  backendStatus.value = 'checking'
  try {
    const res = await fetch(`${getApiBaseUrl()}/health`, { cache: 'no-store' })
    const health = res.ok ? await res.json() : null
    if (res.ok && health?.status === 'ok') {
      backendStatus.value = 'healthy'
    } else {
      backendStatus.value = 'unreachable'
    }
  } catch {
    backendStatus.value = 'unreachable'
  }
}

async function handleRequestNotification() {
  isRequestingNotif.value = true
  notifFeedback.value = null
  try {
    const success = await notifStore.requestPermissionAndRegister()
    if (success) {
      notifFeedback.value = '✓ 푸시 알림 권한이 허용되고 기기가 성공적으로 등록되었습니다.'
    } else if (notifStore.permission === 'denied') {
      notifFeedback.value = '브라우저 설정에서 알림이 차단되어 있습니다. 브라우저 사이트 설정에서 권한을 허용해주세요.'
    } else {
      notifFeedback.value = '알림 권한이 설정되지 않았거나 현재 환경에서 Web Push가 지원되지 않습니다.'
    }
  } finally {
    isRequestingNotif.value = false
  }
}

async function handleEmailAuth() {
  if (!authEmail.value || !authPassword.value) return
  authSubmitting.value = true
  try {
    if (authMode.value === 'login') {
      await authStore.loginWithEmail(authEmail.value, authPassword.value)
    } else {
      await authStore.signupWithEmail(authEmail.value, authPassword.value)
    }
    authEmail.value = ''
    authPassword.value = ''
  } catch {
    // Error is captured in authStore.error
  } finally {
    authSubmitting.value = false
  }
}

async function handleGuestAuth() {
  authSubmitting.value = true
  try {
    await authStore.loginAsGuest()
  } finally {
    authSubmitting.value = false
  }
}

async function handleGoogleAuth() {
  authSubmitting.value = true
  try {
    await authStore.loginWithGoogle()
  } catch {
    // Error is captured in authStore.error
  } finally {
    authSubmitting.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
}

onMounted(() => {
  activePlatformTab.value = detectedPlatform.value
  checkBackendHealth()
  authStore.init()
  notifStore.checkPermission()
  endpointsStore.loadEndpoints()
})
</script>

<template>
  <div class="settings-view">
    <section class="view-header">
      <h2 class="view-title">환경 설정</h2>
      <p class="view-desc">화면 모드, 알림 권한, PWA 앱 설치 및 사용자 계정을 관리합니다.</p>
    </section>

    <!-- API Endpoints Management -->
    <section class="settings-card" aria-labelledby="api-endpoints-heading">
      <div class="card-title-row">
        <h3 id="api-endpoints-heading" class="card-title">API 엔드포인트 관리 (API Endpoints)</h3>
        <span class="info-badge">외부 데이터 연동</span>
      </div>
      <p class="setting-caption">
        자동 수집(auto-fetching)할 외부 REST API 엔드포인트와 스케줄, 재시도 정책을 등록하고 관리합니다.
      </p>

      <div class="api-endpoints-summary-box">
        <div class="summary-text">
          <strong class="summary-count">등록된 엔드포인트: {{ endpointsStore.endpoints.length }}개</strong>
          <span class="summary-desc">스케줄 자동 수집 및 5회 재시도 규칙(1시간 간격) 설정 가능</span>
        </div>
        <button
          type="button"
          class="setting-api-btn register-api-nav-btn"
          aria-label="API 엔드포인트 등록 화면으로 이동"
          @click="router.push('/register-api')"
        >
          <svg class="nav-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>API 엔드포인트 등록 및 관리</span>
        </button>
      </div>
    </section>
    <section class="settings-card">
      <h3 class="card-title">카카오 연결 유지</h3>
      <p class="setting-caption">계정을 한 번 연결하면 이 브라우저에서 로그인 상태를 유지하고 필요할 때 자동 복원합니다. 팝업을 허용해 주세요.</p>
      <button type="button" class="setting-action-btn" :disabled="kakaoBusy" @click="manageKakao()">카카오 연결 / 복원</button>
      <button type="button" class="setting-sub-btn" :disabled="kakaoBusy" @click="manageKakao(true)">카카오 연결 해제</button>
      <p role="status">{{ kakaoFeedback }}</p>
    </section>
    <!-- 1. Appearance Modes as a List (NO dropdown!) -->
    <section class="settings-card" aria-labelledby="appearance-heading">
      <div class="card-title-row">
        <h3 id="appearance-heading" class="card-title">화면 테마 모드 (Appearance)</h3>
        <span class="info-badge">모노크롬 테마</span>
      </div>
      <p class="setting-caption">
        시스템 설정에 맞추거나 라이트/다크 모드를 목록에서 선택하여 전환합니다.
      </p>

      <ul class="appearance-mode-list" role="radiogroup" aria-label="화면 테마 모드 목록">
        <li
          v-for="item in appearanceOptions"
          :key="item.mode"
          class="appearance-mode-item"
          :class="{ selected: themeStore.mode === item.mode }"
          role="radio"
          :aria-checked="themeStore.mode === item.mode"
          tabindex="0"
          @click="themeStore.setMode(item.mode)"
          @keydown.space.prevent="themeStore.setMode(item.mode)"
          @keydown.enter.prevent="themeStore.setMode(item.mode)"
        >
          <div class="mode-info">
            <div class="mode-title-row">
              <span class="mode-icon" aria-hidden="true">{{ item.icon }}</span>
              <strong class="mode-name">{{ item.name }}</strong>
              <span v-if="themeStore.mode === item.mode" class="current-badge">적용 중</span>
            </div>
            <p class="mode-desc">{{ item.desc }}</p>
          </div>
          <div class="mode-radio-indicator" aria-hidden="true">
            <span v-if="themeStore.mode === item.mode" class="radio-dot" />
          </div>
        </li>
      </ul>
    </section>

    <!-- 2. Push Notifications (Permission Status & Enable Action) -->
    <section class="settings-card" aria-labelledby="notif-heading">
      <div class="card-title-row">
        <h3 id="notif-heading" class="card-title">푸시 알림 (Push Notifications)</h3>
        <span
          class="status-indicator"
          :class="{
            active: notifStore.permission === 'granted',
            denied: notifStore.permission === 'denied',
            inactive: notifStore.permission === 'default'
          }"
        >
          {{
            notifStore.permission === 'granted'
              ? '허용됨 (Active)'
              : notifStore.permission === 'denied'
              ? '차단됨 (Denied)'
              : '미설정 (Default)'
          }}
        </span>
      </div>

      <p class="setting-caption">
        백엔드 스케줄러가 새 브리핑을 수집했을 때 모바일 기기로 푸시 알림을 수신합니다.
      </p>

      <!-- Notification Permission Details -->
      <div class="notif-details">
        <div class="detail-row">
          <span class="detail-label">브라우저 알림 권한 상태:</span>
          <span class="detail-value font-mono font-semibold">
            {{ notifStore.permission }}
            <span v-if="notifStore.permission === 'granted'"> (알림 수신 가능)</span>
            <span v-else-if="notifStore.permission === 'denied'"> (브라우저에서 차단됨)</span>
            <span v-else> (권한 요청 필요)</span>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Web Push API 지원 여부:</span>
          <span class="detail-value">
            {{ notifStore.isSupported ? '지원됨' : '미지원 (iOS는 홈 화면 설치 필요)' }}
          </span>
        </div>
        <div v-if="notifStore.deviceId" class="detail-row">
          <span class="detail-label">등록된 기기 ID:</span>
          <span class="detail-value font-mono ellipsis">{{ notifStore.deviceId }}</span>
        </div>
      </div>

      <!-- Feedback Banner -->
      <div v-if="notifFeedback" class="notif-feedback-box" role="status" aria-live="polite">
        {{ notifFeedback }}
      </div>

      <!-- Action to Enable Notifications when supported -->
      <div class="notif-action-area">
        <button
          v-if="notifStore.isSupported && notifStore.permission !== 'granted'"
          type="button"
          class="setting-action-btn"
          :disabled="isRequestingNotif"
          @click="handleRequestNotification"
        >
          {{ isRequestingNotif ? '권한 요청 중...' : '푸시 알림 권한 허용하기' }}
        </button>

        <button
          v-else-if="notifStore.isSupported && notifStore.permission === 'granted'"
          type="button"
          class="setting-sub-btn"
          :disabled="isRequestingNotif"
          @click="handleRequestNotification"
        >
          {{ isRequestingNotif ? '등록 갱신 중...' : '알림 기기 등록 재확인' }}
        </button>

        <!-- Guidance if permission is denied -->
        <div v-if="notifStore.permission === 'denied'" class="denied-guidance-box">
          <span class="warning-icon">⚠️</span>
          <p class="denied-text">
            브라우저에서 알림 권한이 차단되어 있습니다. 주소창 좌측의 설정/자물쇠 아이콘을 탭하여 알림 권한을 <strong>'허용'</strong>으로 변경해주세요.
          </p>
        </div>

        <!-- Guidance if unsupported (e.g. iOS Safari tab) -->
        <div v-if="!notifStore.isSupported" class="unsupported-guidance-box">
          <span class="warning-icon">ℹ️</span>
          <p class="unsupported-text">
            현재 실행 환경에서는 Web Push가 지원되지 않습니다. <strong>iOS 기기의 경우 아래 'PWA 앱 설치 안내'에 따라 Safari에서 '홈 화면에 추가'한 후 홈 화면 아이콘으로 실행</strong>하시면 알림을 활성화할 수 있습니다.
          </p>
        </div>
      </div>
    </section>

    <!-- 3. Platform-Specific PWA Installation Guidance -->
    <section class="settings-card" aria-labelledby="pwa-guide-heading">
      <div class="card-title-row">
        <h3 id="pwa-guide-heading" class="card-title">PWA 앱 설치 안내 (Platform Guide)</h3>
        <span class="info-badge">PWA 가이드</span>
      </div>
      <p class="setting-caption">
        모아톡을 홈 화면에 앱 형태로 설치하여 독립형 전체화면 실행과 원활한 푸시 알림을 경험하세요.
      </p>

      <!-- Platform Selection Tabs -->
      <nav class="platform-tabs" aria-label="기기별 설치 안내 선택">
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'android' }"
          @click="activePlatformTab = 'android'"
        >
          <span>🤖 Android</span>
          <span v-if="detectedPlatform === 'android'" class="detected-badge">현재 기기</span>
        </button>
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'ios' }"
          @click="activePlatformTab = 'ios'"
        >
          <span>🍎 iOS (Safari)</span>
          <span v-if="detectedPlatform === 'ios'" class="detected-badge">현재 기기</span>
        </button>
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'desktop' }"
          @click="activePlatformTab = 'desktop'"
        >
          <span>💻 Desktop (PC)</span>
          <span v-if="detectedPlatform === 'desktop'" class="detected-badge">현재 기기</span>
        </button>
      </nav>

      <!-- Platform Guides -->
      <div class="platform-guide-content">
        <!-- Android Guide -->
        <div v-if="activePlatformTab === 'android'" class="platform-card">
          <div class="platform-card-header">
            <strong>Android (Chrome / Samsung Internet) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>Chrome 또는 Samsung Internet 브라우저로 Moatok에 접속합니다.</li>
            <li>브라우저 상단 또는 하단의 <strong>더보기 메뉴(⋮)</strong>를 누릅니다.</li>
            <li><strong>'앱 설치'</strong> 또는 <strong>'홈 화면에 추가'</strong>를 선택합니다.</li>
            <li>홈 화면에 추가된 Moatok 아이콘을 눌러 독립형 앱(Standalone)으로 실행합니다.</li>
          </ol>
        </div>

        <!-- iOS Guide -->
        <div v-if="activePlatformTab === 'ios'" class="platform-card ios-card">
          <div class="platform-card-header">
            <strong>iOS / iPadOS (Safari) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>반드시 <strong>Safari 브라우저</strong>로 접속합니다 (카카오톡 인앱 브라우저 등에서는 설치 불가).</li>
            <li>Safari 하단 툴바의 <strong>공유 버튼(네모 위 화살표 모양)</strong>을 탭합니다.</li>
            <li>메뉴를 아래로 스크롤하여 <strong>'홈 화면에 추가'</strong>를 선택하고 완료합니다.</li>
            <li>홈 화면에 생성된 <strong>모아톡 아이콘을 눌러 실행</strong>합니다.</li>
          </ol>
          <div class="ios-alert-box">
            <strong class="ios-alert-title">⚠️ iOS 필수 안내 (iOS 16.4+)</strong>
            <p class="ios-alert-desc">
              Apple 정책상 <strong>iOS 16.4 이상</strong>에서만 PWA 웹 푸시 알림이 지원되며, <strong>반드시 홈 화면에 추가한 후 홈 화면 아이콘으로 실행한 상태</strong>에서만 푸시 알림 권한을 허용하고 수신할 수 있습니다. 일반 Safari 브라우저 탭에서는 알림 기능이 차단됩니다.
            </p>
          </div>
        </div>

        <!-- Desktop Guide -->
        <div v-if="activePlatformTab === 'desktop'" class="platform-card">
          <div class="platform-card-header">
            <strong>Desktop (Chrome / Edge / Safari) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>Chrome 또는 Edge 브라우저 주소창 우측의 <strong>설치 아이콘(⊕)</strong>을 클릭합니다.</li>
            <li>또는 브라우저 메뉴(⋮) > <strong>'Moatok 설치'</strong>를 선택합니다.</li>
            <li>설치 후 데스크톱 독립 창 및 작업 표시줄에 고정하여 편리하게 사용합니다.</li>
          </ol>
        </div>
      </div>
    </section>

    <!-- 4. User Account & Logout -->
    <section class="settings-card" aria-labelledby="auth-heading">
      <div class="card-title-row">
        <h3 id="auth-heading" class="card-title">사용자 계정 (Firebase Auth)</h3>
        <span
          class="status-indicator"
          :class="{
            active: authStore.isAuthenticated,
            inactive: !authStore.isAuthenticated && !authStore.sessionExpired,
            expired: authStore.sessionExpired
          }"
        >
          {{
            authStore.sessionExpired
              ? '세션 만료'
              : authStore.isLoading
              ? '확인 중'
              : authStore.isAuthenticated
              ? (authStore.isAdmin ? '관리자 (Admin)' : '인증됨')
              : '미인증'
          }}
        </span>
      </div>

      <!-- Expired Session Alert Banner -->
      <div v-if="authStore.sessionExpired" class="auth-alert expired-alert">
        <div class="alert-icon">⚠️</div>
        <div class="alert-body">
          <strong>세션이 만료되었습니다</strong>
          <p>보안을 위해 다시 로그인해주세요.</p>
        </div>
      </div>

      <!-- Error Alert Banner -->
      <div v-if="authStore.error" class="auth-alert error-alert">
        <div class="alert-icon">✕</div>
        <div class="alert-body">
          <p>{{ authStore.error }}</p>
        </div>
        <button
          type="button"
          class="alert-dismiss-btn"
          aria-label="오류 메시지 닫기"
          @click="authStore.clearError"
        >
          ✕
        </button>
      </div>

      <!-- Authenticated User Profile with Logout -->
      <div v-if="authStore.isAuthenticated && authStore.profile" class="user-info-box">
        <div class="detail-row">
          <span class="detail-label">사용자 UID:</span>
          <span class="detail-value font-mono ellipsis">{{ authStore.profile.uid }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 이메일:</span>
          <span class="detail-value">{{ authStore.userEmail || '익명 게스트 계정' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 권한:</span>
          <span class="detail-value" :class="{ 'admin-badge': authStore.isAdmin }">
            {{ authStore.isAdmin ? '관리자 (Admin Custom Claim)' : '일반 사용자' }}
          </span>
        </div>

        <div class="auth-actions-row">
          <button
            type="button"
            class="logout-btn"
            :disabled="authStore.isLoading"
            aria-label="계정 로그아웃"
            @click="handleLogout"
          >
            {{ authStore.isLoading ? '처리 중...' : '로그아웃' }}
          </button>
        </div>
      </div>

      <!-- Signed-Out Form with Configurable Methods -->
      <div v-else class="auth-form-box">
        <p class="setting-caption">
          로그인하여 브리핑을 검토하고 보호된 백엔드 API에 접근합니다.
        </p>

        <!-- Method Selector -->
        <div class="auth-method-selector">
          <button
            type="button"
            class="method-btn"
            :class="{ active: selectedMethod === 'email' }"
            @click="selectedMethod = 'email'"
          >
            이메일 로그인
          </button>
          <button
            type="button"
            class="method-btn"
            :class="{ active: selectedMethod === 'anonymous' }"
            @click="selectedMethod = 'anonymous'"
          >
            게스트 (익명)
          </button>
          <button
            type="button"
            class="method-btn"
            :class="{ active: selectedMethod === 'google' }"
            @click="selectedMethod = 'google'"
          >
            Google
          </button>
        </div>

        <!-- 1. Email / Password Authentication -->
        <form
          v-if="selectedMethod === 'email'"
          class="email-auth-form"
          @submit.prevent="handleEmailAuth"
        >
          <div class="form-group">
            <label for="auth-email-input" class="form-label">이메일</label>
            <input
              id="auth-email-input"
              v-model="authEmail"
              type="email"
              required
              autocomplete="username"
              placeholder="user@example.com"
              class="form-input"
              :disabled="authSubmitting || authStore.isLoading"
            />
          </div>

          <div class="form-group">
            <label for="auth-password-input" class="form-label">비밀번호</label>
            <input
              id="auth-password-input"
              v-model="authPassword"
              type="password"
              required
              minlength="6"
              autocomplete="current-password"
              placeholder="6자 이상 비밀번호"
              class="form-input"
              :disabled="authSubmitting || authStore.isLoading"
            />
          </div>

          <div class="form-buttons-row">
            <button
              type="submit"
              class="auth-primary-btn"
              :disabled="authSubmitting || authStore.isLoading"
            >
              {{ authSubmitting ? '처리 중...' : authMode === 'login' ? '로그인' : '회원가입' }}
            </button>
            <button
              type="button"
              class="auth-sub-btn"
              :disabled="authSubmitting || authStore.isLoading"
              @click="authMode = authMode === 'login' ? 'signup' : 'login'"
            >
              {{ authMode === 'login' ? '새 계정 회원가입' : '기존 계정 로그인' }}
            </button>
          </div>
        </form>

        <!-- 2. Anonymous / Guest Sign-in -->
        <div v-else-if="selectedMethod === 'anonymous'" class="anonymous-auth-box">
          <p class="setting-caption">
            별도 가입 없이 익명 계정으로 즉시 브리핑을 검토하고 카카오톡 공유를 시작할 수 있습니다.
          </p>
          <button
            type="button"
            class="auth-primary-btn"
            :disabled="authSubmitting || authStore.isLoading"
            @click="handleGuestAuth"
          >
            {{ authSubmitting ? '처리 중...' : '게스트로 시작하기 (익명 인증)' }}
          </button>
        </div>

        <!-- 3. Google Sign-in -->
        <div v-else-if="selectedMethod === 'google'" class="google-auth-box">
          <p class="setting-caption">
            Google 계정으로 안전하게 Firebase 인증을 수행합니다.
          </p>
          <button
            type="button"
            class="auth-primary-btn"
            :disabled="authSubmitting || authStore.isLoading"
            @click="handleGoogleAuth"
          >
            {{ authSubmitting ? '처리 중...' : 'Google 계정으로 로그인' }}
          </button>
        </div>
      </div>
    </section>

    <!-- 5. System Health & Sharing Policy -->
    <section class="settings-card highlight-card" aria-labelledby="policy-heading">
      <div class="card-title-row">
        <h3 id="policy-heading" class="card-title">카카오톡 공유 정책 및 시스템 상태</h3>
        <span class="notice-tag">필독</span>
      </div>
      <div class="policy-content">
        <p class="policy-lead">
          <strong>Moatok은 카카오톡 채팅방에 자동으로 게시하지 않습니다.</strong>
        </p>
        <ul class="policy-list">
          <li>
            <strong>사용자 주도 전송:</strong> 카카오 플랫폼 운영 정책 및 계정 안전을 위해, 사용자가 직접 내용을 검토한 후 대상 오픈채팅방이나 친구를 선택하여 공유하는 방식을 준수합니다.
          </li>
          <li>
            <strong>안전한 백엔드 역할:</strong> Python Flask 백엔드는 RSS 수집, 사실 기반 요약 포맷팅, Firestore 중복 방지 저장 및 PWA 푸시 알림까지만 자동으로 수행합니다.
          </li>
          <li>
            <strong>백엔드 연결 상태:</strong>
            <span class="font-mono">
              {{ backendStatus === 'healthy' ? '✓ 정상 연결됨 (/health OK)' : backendStatus === 'checking' ? '확인 중...' : '연결 실패' }}
            </span>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  padding-bottom: 40px;
}

.view-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.view-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.view-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.settings-card {
  padding: 16px;
  border-radius: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.setting-caption {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.45;
  margin: 0;
}

.info-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

/* 1. Appearance Modes as a List */
.appearance-mode-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.appearance-mode-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.15s ease;
}

.appearance-mode-item:hover {
  border-color: var(--border-strong);
}

.appearance-mode-item.selected {
  border-color: var(--accent-action);
  background-color: var(--bg-surface);
}

.mode-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
}

.mode-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-icon {
  font-size: 15px;
}

.mode-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.current-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.mode-desc {
  font-size: 11.5px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.4;
}

.mode-radio-indicator {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 12px;
  flex-shrink: 0;
}

.appearance-mode-item.selected .mode-radio-indicator {
  border-color: var(--accent-action);
}

.radio-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent-action);
}

/* 2. Notifications */
.status-indicator {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-muted);
}

.status-indicator.active {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.status-indicator.denied {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
}

.notif-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  font-size: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-primary);
  text-align: right;
}

.font-mono {
  font-family: var(--font-mono);
}

.font-semibold {
  font-weight: 600;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.notif-feedback-box {
  padding: 9px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.notif-action-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-action-btn {
  width: 100%;
  padding: 12px 16px;
  border-radius: 8px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: opacity 0.15s ease, background-color 0.15s ease, transform 0.1s ease;
}

.setting-action-btn:hover:not(:disabled) {
  background-color: var(--accent-action-hover);
}

.setting-action-btn:active:not(:disabled) {
  transform: scale(0.99);
}

.setting-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.setting-sub-btn {
  width: 100%;
  padding: 10px 14px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.1s ease;
}

.setting-sub-btn:hover:not(:disabled) {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.setting-sub-btn:active:not(:disabled) {
  transform: scale(0.99);
}

.setting-sub-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.denied-guidance-box,
.unsupported-guidance-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px dashed var(--border-strong);
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--text-secondary);
}

.warning-icon {
  font-size: 13px;
}

.denied-text,
.unsupported-text {
  margin: 0;
}

/* 3. Platform PWA Guidance */
.platform-tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.platform-tab-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.platform-tab-btn.active {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-color: var(--accent-action);
}

.detected-badge {
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  background-color: var(--bg-surface);
  color: var(--text-primary);
}

.platform-card {
  padding: 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
}

.platform-card-header {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.step-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.ios-alert-box {
  margin-top: 6px;
  padding: 9px 11px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ios-alert-title {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.ios-alert-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.45;
  margin: 0;
}

/* 4. Auth & Logout */
.user-info-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  font-size: 12px;
}

.admin-badge {
  font-weight: 700;
  color: var(--text-primary);
}

.auth-actions-row {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.logout-btn {
  padding: 9px 18px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.auth-form-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auth-method-selector {
  display: flex;
  gap: 6px;
}

.method-btn {
  flex: 1;
  padding: 8px 10px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.method-btn.active {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-color: var(--accent-action);
}

.email-auth-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  padding: 10px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-size: 13px;
}

.form-input:focus {
  outline: none;
  border-color: var(--border-strong);
}

.form-buttons-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.auth-primary-btn {
  width: 100%;
  padding: 11px 16px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.auth-primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-sub-btn {
  background: none;
  border: none;
  padding: 6px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}

.auth-sub-btn:hover {
  color: var(--text-primary);
}

.auth-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
}

.expired-alert {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
}

.error-alert {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
}

.alert-dismiss-btn {
  background: none;
  border: none;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  margin-left: auto;
}

/* 5. Policy */
.policy-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.policy-lead {
  margin: 0;
  color: var(--text-primary);
}

.policy-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notice-tag {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

/* API Endpoints Section */
.api-endpoints-summary-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
}

.summary-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.summary-count {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.setting-api-btn {
  width: 100%;
  padding: 12px 16px;
  border-radius: 8px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: opacity 0.15s ease, background-color 0.15s ease, transform 0.1s ease;
}

.setting-api-btn:hover {
  background-color: var(--accent-action-hover);
}

.setting-api-btn:active {
  transform: scale(0.99);
}

.register-api-nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-decoration: none;
}

.nav-btn-icon {
  width: 14px;
  height: 14px;
}
</style>
