<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '@/stores/messages'
import { useEndpointsStore } from '@/stores/endpoints'
import type { ShareMessage } from '@/types'
import MessageCard from '@/components/MessageCard.vue'
import ShareModal from '@/components/ShareModal.vue'
import NotificationBanner from '@/components/NotificationBanner.vue'

const router = useRouter()
const messagesStore = useMessagesStore()
const endpointsStore = useEndpointsStore()

const selectedMessage = ref<ShareMessage | null>(null)
const isModalOpen = ref(false)
const fetchFeedback = ref<string | null>(null)

// Pull-to-refresh mobile touch state
const touchStartY = ref(0)
const pullDistance = ref(0)
const pullThreshold = 65
const isPulling = ref(false)
const pullReady = ref(false)

function handleTouchStart(e: TouchEvent) {
  if (typeof window === 'undefined') return
  if (window.scrollY > 0) return
  if (messagesStore.loading || messagesStore.refreshing) return

  touchStartY.value = e.touches[0].clientY
  isPulling.value = true
}

function handleTouchMove(e: TouchEvent) {
  if (!isPulling.value) return
  if (window.scrollY > 0) {
    pullDistance.value = 0
    pullReady.value = false
    return
  }

  const currentY = e.touches[0].clientY
  const rawDiff = currentY - touchStartY.value
  if (rawDiff > 0) {
    pullDistance.value = Math.min(Math.floor(rawDiff * 0.45), 90)
    pullReady.value = pullDistance.value >= pullThreshold
  } else {
    pullDistance.value = 0
    pullReady.value = false
  }
}

async function handleTouchEnd() {
  if (!isPulling.value) return
  isPulling.value = false

  if (pullReady.value) {
    await refresh()
  }
  pullDistance.value = 0
  pullReady.value = false
}

async function refresh() {
  await messagesStore.fetchPending(true)
}

function handleCardSelect(msg: ShareMessage) {
  router.push({ name: 'message-detail', params: { id: msg.id } })
}

function openReviewModal(msg: ShareMessage) {
  selectedMessage.value = msg
  isModalOpen.value = true
}

const isPreviewMode = ref(false)
const hasFetchedCards = computed(() => messagesStore.pendingMessages.some(message => !!message.endpoint_id))

function dismissErrorToPreview() {
  messagesStore.error = null
  isPreviewMode.value = true
}

async function handleFetchCard(msg: ShareMessage) {
  fetchFeedback.value = null
  if (msg.endpoint_id) {
    const res = await endpointsStore.triggerFetch(msg.endpoint_id, true)
    if (res.success) {
      fetchFeedback.value = '✓ 데이터를 성공적으로 가져왔습니다.'
      setTimeout(() => {
        if (fetchFeedback.value?.startsWith('✓')) fetchFeedback.value = null
      }, 4000)
    } else {
      fetchFeedback.value = `⚠️ 수동 가져오기 실패: ${res.message}`
    }
  } else {
    await refresh()
  }
}

onMounted(() => {
  endpointsStore.loadEndpoints()
  messagesStore.fetchPending()
})
</script>

<template>
  <main
    class="pending-view"
    @touchstart.passive="handleTouchStart"
    @touchmove.passive="handleTouchMove"
    @touchend="handleTouchEnd"
  >
    <!-- Mobile Pull-to-Refresh Indicator -->
    <div
      v-if="pullDistance > 0 || messagesStore.refreshing"
      class="pull-refresh-bar"
      :style="{ height: `${Math.max(pullDistance, messagesStore.refreshing ? 48 : 0)}px` }"
      role="status"
      aria-live="polite"
    >
      <div class="pull-refresh-content">
        <svg
          class="pull-icon"
          :class="{ spinning: messagesStore.refreshing, ready: pullReady && !messagesStore.refreshing }"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path d="M23 4v6h-6" />
          <path d="M1 20v-6h6" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
        <span class="pull-text">
          {{ messagesStore.refreshing ? '브리핑을 불러오는 중...' : pullReady ? '손을 놓으면 새로고침' : '당겨서 새로고침' }}
        </span>
      </div>
    </div>

    <NotificationBanner />

    <!-- Fetch feedback banner -->
    <div v-if="fetchFeedback" class="fetch-feedback-banner" role="status" aria-live="polite">
      <span>{{ fetchFeedback }}</span>
      <button type="button" class="feedback-close-btn" aria-label="닫기" @click="fetchFeedback = null">✕</button>
    </div>

    <!-- View Header with Title, Count, and Refresh Action -->
    <header class="view-header">
      <div class="header-main-row">
        <div class="header-titles">
          <h1 class="view-title">공유 대기 브리핑</h1>
          <span
            class="count-pill"
            :aria-label="`대기 중인 브리핑 ${messagesStore.pendingCount}건`"
          >
            {{ messagesStore.pendingCount }}건
          </span>
        </div>

        <div class="header-action-group">
          <button
            type="button"
            class="register-api-btn"
            aria-label="API 엔드포인트 등록"
            @click="router.push('/register-api')"
          >
            <svg class="nav-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>API 등록</span>
          </button>

          <button
            type="button"
            class="refresh-action-btn"
            :disabled="messagesStore.loading || messagesStore.refreshing"
            :aria-label="messagesStore.refreshing ? '새로고침 진행 중' : '브리핑 목록 새로고침'"
            @click="refresh"
          >
            <svg
              class="refresh-icon"
              :class="{ spinning: messagesStore.refreshing }"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path d="M23 4v6h-6" />
              <path d="M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span class="refresh-btn-text">새로고침</span>
          </button>
        </div>
      </div>

      <p class="view-desc">
        수집된 콘텐츠를 검토하고 카카오톡 대상 채팅방으로 직접 공유하세요.
      </p>
    </header>

    <p v-if="messagesStore.error && hasFetchedCards" role="status" class="fetch-feedback-banner">서버 목록을 불러오지 못했습니다. 이 기기에 저장된 브리핑을 표시합니다.</p>
    <p v-if="messagesStore.storageWarning" role="status">{{ messagesStore.storageWarning }}</p>
    <!-- 1. Loading State (Accessible Skeleton Cards) -->
    <div
      v-if="messagesStore.loading && !messagesStore.refreshing && !hasFetchedCards"
      class="loading-skeleton-list"
      role="status"
      aria-label="공유 대기 브리핑을 불러오는 중입니다"
      aria-busy="true"
    >
      <div v-for="i in 3" :key="i" class="skeleton-card">
        <div class="skeleton-header">
          <div class="skeleton-pill"></div>
          <div class="skeleton-time"></div>
        </div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-body-1"></div>
        <div class="skeleton-line skeleton-body-2"></div>
        <div class="skeleton-footer">
          <div class="skeleton-btn"></div>
          <div class="skeleton-btn"></div>
        </div>
      </div>
    </div>

    <!-- 2. Error State -->
    <div
      v-else-if="messagesStore.error && !messagesStore.loading && !hasFetchedCards"
      class="error-state-card"
      role="alert"
    >
      <div class="error-icon" aria-hidden="true">⚠️</div>
      <div class="error-content">
        <h2 class="error-title">브리핑을 불러오지 못했습니다</h2>
        <p class="error-desc">{{ messagesStore.error }}</p>
      </div>
      <div class="error-actions-group">
        <button
          type="button"
          class="retry-btn fetch-btn"
          aria-label="브리핑 목록 다시 시도"
          @click="refresh"
        >
          Fetch
        </button>
        <button
          v-if="messagesStore.pendingCount > 0"
          type="button"
          class="preview-sample-btn"
          @click="dismissErrorToPreview"
        >
          샘플 브리핑 둘러보기 ({{ messagesStore.pendingCount }}건)
        </button>
      </div>
    </div>

    <!-- 3. Empty State -->
    <div
      v-else-if="messagesStore.pendingCount === 0"
      class="empty-state"
      role="status"
    >
      <div class="empty-icon" aria-hidden="true">✓</div>
      <h2 class="empty-title">공유 대기 브리핑이 없습니다</h2>
      <p class="empty-desc">
        현재 검토할 새 콘텐츠가 없습니다. 백엔드 스케줄러가 새 RSS 및 소스를 수집하면 이곳에 등록됩니다.
      </p>
      <button
        type="button"
        class="refresh-inline-btn"
        :disabled="messagesStore.refreshing"
        @click="refresh"
      >
        새로고침 확인
      </button>
    </div>

    <!-- 4. Message List -->
    <div
      v-else
      class="message-list"
      role="feed"
      aria-label="공유 대기 브리핑 목록"
    >
      <div v-if="isPreviewMode" class="preview-mode-banner" role="status">
        <div class="preview-banner-text">
          <span class="preview-badge">미리보기</span>
          <span>서버 연결 전 로컬 샘플 브리핑을 표시 중입니다.</span>
        </div>
        <button type="button" class="preview-dismiss-btn" aria-label="안내 닫기" @click="isPreviewMode = false">✕</button>
      </div>
      <MessageCard
        v-for="msg in messagesStore.pendingMessages"
        :key="msg.id"
        :message="msg"
        @select="handleCardSelect"
        @review="openReviewModal"
        @fetch="handleFetchCard"
      />
    </div>

    <!-- Review & Share Modal -->
    <ShareModal
      v-model="isModalOpen"
      :message="selectedMessage"
    />
  </main>
</template>

<style scoped>
.pending-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
  min-height: calc(100vh - 120px);
}

.pull-refresh-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: var(--bg-surface-elevated);
  border-bottom: 1px solid var(--border-subtle);
  transition: height 0.15s ease-out;
}

.pull-refresh-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.pull-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s ease;
}

.pull-icon.ready {
  transform: rotate(180deg);
}

.pull-icon.spinning,
.refresh-icon.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.view-header {
  padding: 16px 16px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-main-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-titles {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.count-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.view-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.4;
}

.header-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.register-api-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  min-height: 36px;
  transition: all 0.15s ease;
}

.register-api-btn:hover {
  background-color: var(--accent-action-hover);
  opacity: 0.9;
}

.nav-btn-icon {
  width: 13px;
  height: 13px;
}

.fetch-feedback-banner {
  margin: 0 16px 4px 16px;
  padding: 8px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.feedback-close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 2px 4px;
}

.refresh-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  min-height: 36px;
  transition: all 0.15s ease;
}

.refresh-action-btn:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.refresh-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-icon {
  width: 14px;
  height: 14px;
}

/* Skeleton Loading State */
.loading-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}

.skeleton-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skeleton-pill {
  width: 60px;
  height: 18px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
}

.skeleton-time {
  width: 50px;
  height: 14px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
}

.skeleton-line {
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
}

.skeleton-title {
  width: 80%;
  height: 20px;
}

.skeleton-body-1 {
  width: 100%;
  height: 14px;
}

.skeleton-body-2 {
  width: 65%;
  height: 14px;
}

.skeleton-footer {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 8px;
  margin-top: 4px;
}

.skeleton-btn {
  height: 38px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
}

/* Error State */
.error-state-card {
  margin: 16px;
  padding: 16px;
  border-radius: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.error-icon {
  font-size: 28px;
}

.error-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.error-desc {
  font-size: 12.5px;
  color: var(--text-muted);
  margin-top: 4px;
}

.error-actions-group {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  width: 100%;
}

.retry-btn {
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  min-height: 40px;
  border: none;
  transition: opacity 0.15s ease;
}

.retry-btn:hover {
  opacity: 0.85;
}

.preview-sample-btn {
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  min-height: 40px;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.preview-sample-btn:hover {
  background-color: var(--bg-surface-hover);
  border-color: var(--border-strong);
}

.preview-mode-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.preview-banner-text {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.preview-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.preview-dismiss-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  padding: 2px 6px;
  margin-left: auto;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
  margin: 16px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: 12px;
  gap: 10px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  max-width: 320px;
}

.refresh-inline-btn {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  min-height: 40px;
}

.refresh-inline-btn:hover {
  background-color: var(--bg-surface-hover);
}

/* Message List */
.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}
</style>
