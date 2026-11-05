<script setup lang="ts">
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { offlineReady, needRefresh, updateServiceWorker } = useRegisterSW({
  immediate: true,
  onRegisteredSW(swUrl, registration) {
    if (import.meta.env.DEV) {
      console.log('PWA Service Worker registered:', swUrl, registration)
    }
  },
  onRegisterError(error) {
    console.warn('PWA Service Worker registration error:', error)
  }
})

function closePrompt() {
  needRefresh.value = false
  offlineReady.value = false
}

async function handleUpdate() {
  await updateServiceWorker(true)
}
</script>

<template>
  <aside
    v-if="needRefresh"
    class="reload-prompt"
    role="alert"
    aria-live="assertive"
    aria-label="앱 업데이트 알림"
  >
    <div class="prompt-content">
      <div class="prompt-icon">⚡</div>
      <div class="prompt-text">
        <strong class="prompt-title">새 버전 사용 가능</strong>
        <p class="prompt-desc">최신 콘텐츠 수집 기능과 버그 수정이 적용되었습니다.</p>
      </div>
    </div>
    <div class="prompt-actions">
      <button type="button" class="btn-update" @click="handleUpdate">
        업데이트 (새로고침)
      </button>
      <button type="button" class="btn-dismiss" aria-label="닫기" @click="closePrompt">
        나중에
      </button>
    </div>
  </aside>

  <aside
    v-else-if="offlineReady"
    class="reload-prompt offline-ready"
    role="status"
    aria-label="오프라인 준비 완료"
  >
    <div class="prompt-content">
      <div class="prompt-icon">✓</div>
      <div class="prompt-text">
        <strong class="prompt-title">오프라인 사용 준비 완료</strong>
        <p class="prompt-desc">네트워크가 불안정해도 기본 앱 화면을 열 수 있습니다.</p>
      </div>
    </div>
    <button type="button" class="btn-dismiss" aria-label="닫기" @click="offlineReady = false">
      확인
    </button>
  </aside>
</template>

<style scoped>
.reload-prompt {
  position: fixed;
  bottom: calc(72px + var(--sab));
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 448px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-shadow: var(--shadow-md);
  z-index: 60;
  animation: slideUp 0.25s ease-out;
}

@keyframes slideUp {
  from {
    transform: translate(-50%, 20px);
    opacity: 0;
  }
  to {
    transform: translate(-50%, 0);
    opacity: 1;
  }
}

.prompt-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.prompt-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.prompt-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.prompt-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.prompt-desc {
  font-size: 11.5px;
  color: var(--text-secondary);
  line-height: 1.35;
}

.prompt-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.btn-update {
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  white-space: nowrap;
  transition: opacity 0.15s ease;
}

.btn-update:hover {
  opacity: 0.9;
}

.btn-dismiss {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 6px 8px;
  border-radius: 4px;
  background: transparent;
}

.btn-dismiss:hover {
  color: var(--text-primary);
}
</style>
