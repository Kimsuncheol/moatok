<script setup lang="ts">
import { ref } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

const notifStore = useNotificationsStore()
const dismissed = ref(false)
const requesting = ref(false)

async function handleEnable() {
  requesting.value = true
  try {
    await notifStore.requestPermissionAndRegister()
  } finally {
    requesting.value = false
  }
}
</script>

<template>
  <aside
    v-if="notifStore.isSupported && notifStore.permission === 'default' && !dismissed"
    class="notif-banner"
    aria-label="알림 설정 안내"
  >
    <div class="banner-content">
      <div class="banner-icon">🔔</div>
      <div class="banner-text">
        <span class="banner-title">새 브리핑 도착 알림 받기</span>
        <span class="banner-desc">새로운 공유 대기 콘텐츠가 수집되면 즉시 알려드립니다.</span>
      </div>
    </div>
    <div class="banner-actions">
      <button
        type="button"
        class="enable-btn"
        :disabled="requesting"
        @click="handleEnable"
      >
        {{ requesting ? '설정 중...' : '알림 켜기' }}
      </button>
      <button
        type="button"
        class="dismiss-btn"
        aria-label="닫기"
        @click="dismissed = true"
      >
        ✕
      </button>
    </div>
  </aside>
</template>

<style scoped>
.notif-banner {
  margin: 12px 16px 0 16px;
  padding: 10px 12px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.banner-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.banner-text {
  display: flex;
  flex-direction: column;
}

.banner-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.banner-desc {
  font-size: 11px;
  color: var(--text-muted);
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.enable-btn {
  font-size: 12px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  transition: opacity 0.15s ease;
}

.enable-btn:disabled {
  opacity: 0.6;
}

.dismiss-btn {
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px;
}

.dismiss-btn:hover {
  color: var(--text-primary);
}
</style>
