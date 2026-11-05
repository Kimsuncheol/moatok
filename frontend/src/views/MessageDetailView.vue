<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '@/stores/messages'
import type { ShareMessage } from '@/types'
import ShareModal from '@/components/ShareModal.vue'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const messagesStore = useMessagesStore()
const message = ref<ShareMessage | null>(null)
const loading = ref(true)
const isModalOpen = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    message.value = await messagesStore.fetchById(props.id)
  } finally {
    loading.value = false
  }
})

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<template>
  <div class="detail-view">
    <div class="top-bar">
      <button type="button" class="back-btn" @click="goBack">
        ← 뒤로가기
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner" />
      <span>브리핑 정보를 불러오는 중...</span>
    </div>

    <div v-else-if="!message" class="not-found-state">
      <h3>브리핑을 찾을 수 없습니다.</h3>
      <button type="button" class="back-home-btn" @click="router.push('/')">
        목록으로 이동
      </button>
    </div>

    <article v-else class="detail-card">
      <div class="card-status-row">
        <span class="status-badge" :class="message.kakao_shared ? 'badge-shared' : 'badge-pending'">
          {{ message.kakao_shared ? '공유 완료' : '공유 대기' }}
        </span>
        <span class="date-text">
          {{ new Date(message.created_at).toLocaleString('ko-KR') }}
        </span>
      </div>

      <h1 class="detail-title">{{ message.title }}</h1>

      <div class="body-box">
        <pre class="body-text">{{ message.body }}</pre>
      </div>

      <div v-if="message.target_url" class="url-box">
        <span class="url-label">원문 링크:</span>
        <a :href="message.target_url" target="_blank" rel="noopener noreferrer" class="url-href">
          {{ message.target_url }}
        </a>
      </div>

      <button type="button" class="primary-share-btn" @click="isModalOpen = true">
        카카오톡으로 공유하기 (검토 창 열기)
      </button>
    </article>

    <ShareModal
      v-model="isModalOpen"
      :message="message"
      @shared="(updated) => (message = updated)"
    />
  </div>
</template>

<style scoped>
.detail-view {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 32px;
}

.top-bar {
  display: flex;
  align-items: center;
}

.back-btn {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.back-btn:hover {
  color: var(--text-primary);
}

.loading-state,
.not-found-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  gap: 12px;
  color: var(--text-muted);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.back-home-btn {
  padding: 8px 16px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

.detail-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: var(--shadow-sm);
}

.card-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-pending {
  background-color: var(--badge-pending-bg);
  color: var(--badge-pending-text);
}

.badge-shared {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.date-text {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.4px;
}

.body-box {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 14px;
}

.body-text {
  font-family: var(--font-sans);
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.url-box {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  overflow: hidden;
}

.url-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.url-href {
  color: var(--text-secondary);
  text-decoration: underline;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.primary-share-btn {
  margin-top: 4px;
  width: 100%;
  padding: 12px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
}

.primary-share-btn:hover {
  background-color: var(--accent-action-hover);
}
</style>
