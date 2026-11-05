<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppearanceToggle from '@/components/AppearanceToggle.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

const notifStore = useNotificationsStore()
const authStore = useAuthStore()

const backendStatus = ref<'checking' | 'healthy' | 'unreachable'>('checking')
const isRequestingNotif = ref(false)

async function checkBackendHealth() {
  backendStatus.value = 'checking'
  try {
    const res = await fetch('/health')
    if (res.ok) {
      backendStatus.value = 'healthy'
    } else {
      backendStatus.value = 'unreachable'
    }
  } catch {
    backendStatus.value = 'unreachable'
  }
}

async function requestNotification() {
  isRequestingNotif.value = true
  try {
    await notifStore.requestPermissionAndRegister()
  } finally {
    isRequestingNotif.value = false
  }
}

onMounted(() => {
  checkBackendHealth()
  authStore.init()
})
</script>

<template>
  <div class="settings-view">
    <section class="view-header">
      <h2 class="view-title">환경 설정</h2>
      <p class="view-desc">화면 모드, 알림 권한, 사용자 인증 및 공유 정책을 관리합니다.</p>
    </section>

    <!-- 1. Appearance Mode (Segmented Control - NO dropdown!) -->
    <section class="settings-card">
      <div class="card-title-row">
        <h3 class="card-title">화면 테마 (Appearance)</h3>
        <span class="info-badge">단색 모노크롬</span>
      </div>
      <p class="setting-caption">
        시스템 설정에 맞추거나 라이트/다크 모드를 수동으로 전환합니다.
      </p>
      <div class="toggle-container">
        <AppearanceToggle />
      </div>
    </section>

    <!-- 2. KakaoTalk Sharing Policy (Architectural Boundary) -->
    <section class="settings-card highlight-card">
      <div class="card-title-row">
        <h3 class="card-title">카카오톡 공유 정책 안내</h3>
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
            <strong>무단 스크래핑/오토스팸 방지:</strong> 카카오톡 엑세스 토큰이나 서비스 계정 키를 Firestore에 저장하지 않습니다.
          </li>
        </ul>
      </div>
    </section>

    <!-- 3. Push Notifications (FCM) -->
    <section class="settings-card">
      <div class="card-title-row">
        <h3 class="card-title">푸시 알림 (Firebase Cloud Messaging)</h3>
        <span class="status-indicator" :class="notifStore.permission === 'granted' ? 'active' : 'inactive'">
          {{ notifStore.permission === 'granted' ? '활성' : '미허용' }}
        </span>
      </div>
      <p class="setting-caption">
        백엔드 스케줄러가 새 브리핑을 수집했을 때 모바일 기기로 알림을 받습니다.
      </p>

      <div class="notif-details">
        <div class="detail-row">
          <span class="detail-label">브라우저 알림 권한:</span>
          <span class="detail-value font-mono">{{ notifStore.permission }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">등록된 기기 ID:</span>
          <span class="detail-value font-mono ellipsis">{{ notifStore.deviceId }}</span>
        </div>
      </div>

      <button
        v-if="notifStore.permission !== 'granted'"
        type="button"
        class="setting-action-btn"
        :disabled="isRequestingNotif"
        @click="requestNotification"
      >
        {{ isRequestingNotif ? '권한 요청 중...' : '푸시 알림 권한 허용하기' }}
      </button>
    </section>

    <!-- 4. User Account & Firebase Authentication -->
    <section class="settings-card">
      <div class="card-title-row">
        <h3 class="card-title">사용자 인증 (Firebase Auth)</h3>
        <span class="status-indicator" :class="authStore.user || authStore.profile ? 'active' : 'inactive'">
          {{ authStore.user || authStore.profile ? '인증됨' : '게스트' }}
        </span>
      </div>

      <div v-if="authStore.profile" class="user-info-box">
        <div class="detail-row">
          <span class="detail-label">사용자 UID:</span>
          <span class="detail-value font-mono ellipsis">{{ authStore.profile.uid }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 권한:</span>
          <span class="detail-value">
            {{ authStore.profile.is_admin ? '관리자 (Admin)' : '일반 사용자' }}
          </span>
        </div>
        <button type="button" class="logout-btn" @click="authStore.logout">
          로그아웃
        </button>
      </div>

      <div v-else class="guest-box">
        <p class="setting-caption">
          로그인 없이 게스트 모드로 브리핑을 검토하거나 Firebase 익명 로그인을 진행할 수 있습니다.
        </p>
        <button type="button" class="setting-action-btn" @click="authStore.loginAsGuest">
          게스트 로그인 (익명 인증)
        </button>
      </div>
    </section>

    <!-- 5. Backend Connection & Health -->
    <section class="settings-card">
      <div class="card-title-row">
        <h3 class="card-title">Flask REST API 연결</h3>
        <span
          class="status-indicator"
          :class="backendStatus === 'healthy' ? 'active' : 'inactive'"
        >
          {{ backendStatus === 'healthy' ? '연결 정상 (200)' : backendStatus === 'checking' ? '확인 중' : '오프라인' }}
        </span>
      </div>
      <p class="setting-caption">
        백엔드 수집 엔진: Python Flask REST API & Cloud Firestore
      </p>
      <button type="button" class="refresh-health-btn" @click="checkBackendHealth">
        연결 상태 재확인
      </button>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  padding-bottom: 32px;
}

.view-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.view-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.view-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.settings-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: var(--shadow-sm);
}

.highlight-card {
  border-left: 3px solid var(--accent-action);
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.info-badge {
  font-size: 10.5px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
}

.notice-tag {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.status-indicator {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-indicator.active {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.status-indicator.inactive {
  background-color: var(--bg-surface-elevated);
  color: var(--text-muted);
}

.setting-caption {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.toggle-container {
  margin-top: 4px;
}

.policy-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.policy-lead {
  color: var(--text-primary);
}

.policy-list {
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notif-details,
.user-info-box {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  gap: 12px;
}

.detail-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-primary);
  font-weight: 600;
}

.font-mono {
  font-family: var(--font-mono);
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.setting-action-btn {
  margin-top: 4px;
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-size: 13px;
  font-weight: 600;
  transition: opacity 0.15s ease;
}

.setting-action-btn:disabled {
  opacity: 0.6;
}

.logout-btn {
  margin-top: 6px;
  padding: 6px;
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: underline;
  text-align: right;
}

.refresh-health-btn {
  padding: 8px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  align-self: flex-start;
}

.refresh-health-btn:hover {
  color: var(--text-primary);
}
</style>
