<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import { ref, onMounted } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
const notifStore = useNotificationsStore()
const isRequestingNotif = ref(false)
const notifFeedback = ref<string | null>(null)
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

onMounted(() => notifStore.checkPermission())
</script>
<template>
  <SettingsPage title="푸시 알림">
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
          <span class="detail-label">알림 권한 상태:</span>
          <span class="detail-value permission-value font-semibold">
            <span class="font-mono">{{ notifStore.permission }}</span>
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

      </SettingsPage>
</template>
