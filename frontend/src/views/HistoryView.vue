<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '@/stores/messages'
import type { ShareMessage } from '@/types'

const router = useRouter()
const messagesStore = useMessagesStore()

const filter = ref<'all' | 'confirmed' | 'started'>('all')
const confirmingId = ref<string | null>(null)
const confirmFeedback = ref<string | null>(null)

function isConfirmed(m: ShareMessage): boolean {
  return m.kakao_shared === true || m.status === 'shared' || m.status === 'shared_by_user'
}

function isStarted(m: ShareMessage): boolean {
  return (m.share_attempt_count !== undefined && m.share_attempt_count > 0) || !!m.last_share_attempt_at
}

// Show share attempts and confirmed results ONLY when supported by reliable backend events
const verifiableHistory = computed(() => {
  return messagesStore.historyMessages.filter((m) => isConfirmed(m) || isStarted(m))
})

const filteredHistory = computed(() => {
  return verifiableHistory.value.filter((m) => {
    if (filter.value === 'confirmed') return isConfirmed(m)
    if (filter.value === 'started') return isStarted(m) && !isConfirmed(m)
    return true
  })
})

const confirmedCount = computed(() => verifiableHistory.value.filter(isConfirmed).length)
const startedCount = computed(() => verifiableHistory.value.filter((m) => isStarted(m) && !isConfirmed(m)).length)

function formatDate(isoString?: string | null): string {
  if (!isoString) return '-'
  try {
    const d = new Date(isoString)
    return new Intl.DateTimeFormat('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  } catch {
    return isoString
  }
}

function formatChannelName(channel?: string | null): string {
  if (!channel) return '기본 채널'
  switch (channel) {
    case 'kakao_sdk':
      return '카카오톡 JS SDK'
    case 'web_share':
      return '시스템 공유 시트 (Web Share)'
    case 'clipboard':
      return '클립보드 복사'
    case 'kakaotalk_web_pwa':
      return '카카오톡 (Web PWA)'
    case 'kakaotalk_flutter_sdk':
      return '카카오톡 (모바일 SDK)'
    default:
      return channel
  }
}

async function handleRefresh() {
  await messagesStore.fetchHistory(true)
}

async function handleConfirmShare(msg: ShareMessage) {
  confirmingId.value = msg.id
  confirmFeedback.value = null
  try {
    await messagesStore.markAsShared(msg.id, msg.last_share_attempt_channel || 'kakaotalk_web_pwa')
    confirmFeedback.value = `"${msg.title}" 브리핑의 공유 완료가 확정되었습니다.`
    setTimeout(() => {
      confirmFeedback.value = null
    }, 4000)
  } catch (err: any) {
    confirmFeedback.value = err.message || '공유 완료 확정에 실패했습니다.'
  } finally {
    confirmingId.value = null
  }
}

function navigateToDetail(messageId: string) {
  router.push(`/messages/${encodeURIComponent(messageId)}`)
}

onMounted(() => {
  messagesStore.fetchHistory()
})
</script>

<template>
  <div class="history-view">
    <!-- Header -->
    <section class="view-header">
      <div class="header-top-row">
        <div class="header-titles">
          <h2 class="view-title">공유 이력 (History)</h2>
          <span class="count-pill">{{ verifiableHistory.length }}건</span>
        </div>
        <button
          type="button"
          class="refresh-btn"
          :disabled="messagesStore.loading || messagesStore.refreshing"
          aria-label="공유 이력 새로고침"
          @click="handleRefresh"
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
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
      </div>

      <p class="view-desc">
        신뢰할 수 있는 백엔드 이벤트로 기록된 공유 시작(시도) 및 완료 확정 이력입니다.
      </p>

      <!-- Filter Chips -->
      <nav class="filter-chips" aria-label="이력 상태 필터">
        <button
          type="button"
          class="chip-btn"
          :class="{ active: filter === 'all' }"
          @click="filter = 'all'"
        >
          전체 ({{ verifiableHistory.length }})
        </button>
        <button
          type="button"
          class="chip-btn"
          :class="{ active: filter === 'confirmed' }"
          @click="filter = 'confirmed'"
        >
          ✓ 공유 완료 확정 ({{ confirmedCount }})
        </button>
        <button
          type="button"
          class="chip-btn"
          :class="{ active: filter === 'started' }"
          @click="filter = 'started'"
        >
          ⏳ 공유 시작됨 ({{ startedCount }})
        </button>
      </nav>
    </section>

    <!-- Feedback Banner -->
    <div v-if="confirmFeedback" class="feedback-banner" role="status" aria-live="polite">
      {{ confirmFeedback }}
    </div>

    <!-- Loading State -->
    <div v-if="messagesStore.loading && !messagesStore.refreshing && verifiableHistory.length === 0" class="loading-state">
      <div class="spinner" aria-hidden="true" />
      <span>공유 이력을 불러오는 중입니다...</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredHistory.length === 0" class="empty-state">
      <div class="empty-icon">📁</div>
      <h3 class="empty-title">
        {{ filter === 'all' ? '기록된 공유 이력이 없습니다' : '해당 조건의 공유 이력이 없습니다' }}
      </h3>
      <p class="empty-desc">
        공유 대기(Pending) 목록에서 브리핑을 검토하고 카카오톡 공유를 시작하면 백엔드에 안전하게 보존된 이벤트 기록이 여기에 표시됩니다.
      </p>
      <RouterLink to="/" class="go-pending-btn">
        공유 대기 브리핑 보러가기
      </RouterLink>
    </div>

    <!-- History List -->
    <div v-else class="history-list">
      <article
        v-for="msg in filteredHistory"
        :key="msg.id"
        class="history-card"
        :class="{ 'card-confirmed': isConfirmed(msg), 'card-started': !isConfirmed(msg) && isStarted(msg) }"
      >
        <!-- Card Header: Distinction between "Share Started" and "Share Confirmed" -->
        <header class="card-header">
          <div class="badge-group">
            <span
              v-if="isConfirmed(msg)"
              class="status-badge badge-confirmed"
              aria-label="공유 완료 확정"
            >
              ✓ 공유 완료 확정
            </span>
            <span
              v-else-if="isStarted(msg)"
              class="status-badge badge-started"
              aria-label="공유 시작됨 (확인 대기)"
            >
              ⏳ 공유 시작됨 (확인 대기)
            </span>

            <span v-if="msg.source_name" class="source-badge">
              {{ msg.source_name }}
            </span>
          </div>

          <span class="card-date">{{ formatDate(msg.shared_by_user_at || msg.last_share_attempt_at || msg.created_at) }}</span>
        </header>

        <!-- Article Title -->
        <h3 class="card-title">
          <button type="button" class="title-link-btn" @click="navigateToDetail(msg.id)">
            {{ msg.title }}
          </button>
        </h3>

        <!-- Verifiable Backend Events Timeline / Details -->
        <div class="events-box">
          <!-- 1. Share Started Event (Supported only by reliable backend attempt event) -->
          <div v-if="msg.share_attempt_count || msg.last_share_attempt_at" class="event-item event-started">
            <div class="event-icon">📤</div>
            <div class="event-info">
              <div class="event-row">
                <strong class="event-name">공유 시작 (Share Started)</strong>
                <time class="event-time">{{ formatDate(msg.last_share_attempt_at) }}</time>
              </div>
              <p class="event-detail">
                시도 횟수: {{ msg.share_attempt_count || 1 }}회 · 실행 채널: {{ formatChannelName(msg.last_share_attempt_channel) }}
              </p>
            </div>
          </div>

          <!-- 2. Share Confirmed Event (Supported only by reliable backend mark-shared event) -->
          <div v-if="isConfirmed(msg)" class="event-item event-confirmed">
            <div class="event-icon">✅</div>
            <div class="event-info">
              <div class="event-row">
                <strong class="event-name">공유 완료 확정 (Share Confirmed)</strong>
                <time class="event-time">{{ formatDate(msg.shared_by_user_at) }}</time>
              </div>
              <p class="event-detail">
                확정 채널: {{ formatChannelName(msg.last_share_channel) }}
                <span v-if="msg.shared_by_user_id" class="user-subtext">· 확인 사용자: {{ msg.shared_by_user_id }}</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Strict Boundary Disclaimer: Never imply Open Chat room delivery without verification -->
        <div class="openchat-verification-notice">
          <p class="notice-text">
            ℹ️ <strong>전송 대상 안내:</strong> 카카오톡 전송 대상(오픈채팅방/친구/나와의 채팅)은 사용자가 카카오톡 앱 내에서 직접 선택하며, 외부 웹 앱에는 개별 오픈채팅방의 수신 영수증이 제공되지 않습니다. 위 기록은 사용자 주도로 실행된 공유 시도 및 완료 확정 이벤트에 기반합니다.
          </p>
        </div>

        <!-- Action Buttons -->
        <footer class="card-actions">
          <button
            type="button"
            class="detail-action-btn"
            @click="navigateToDetail(msg.id)"
          >
            상세 보기
          </button>

          <!-- Explicit confirmation action if started but not confirmed -->
          <button
            v-if="!isConfirmed(msg)"
            type="button"
            class="confirm-action-btn"
            :disabled="confirmingId === msg.id"
            @click="handleConfirmShare(msg)"
          >
            {{ confirmingId === msg.id ? '확정 저장 중...' : '카카오톡 전송 완료로 확정하기' }}
          </button>
        </footer>
      </article>
    </div>
  </div>
</template>

<style scoped>
.history-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 32px;
}

.view-header {
  padding: 16px 16px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.refresh-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-icon {
  width: 16px;
  height: 16px;
}

.refresh-icon.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.view-desc {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.4;
}

/* Filter Chips */
.filter-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-top: 6px;
  padding-bottom: 2px;
  -webkit-overflow-scrolling: touch;
}

.chip-btn {
  white-space: nowrap;
  font-size: 11.5px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip-btn.active {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-color: var(--accent-action);
}

/* Feedback Banner */
.feedback-banner {
  margin: 0 16px;
  padding: 9px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

/* Loading & Empty State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-default);
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

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
  margin-bottom: 4px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.empty-desc {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.5;
  max-width: 320px;
}

.go-pending-btn {
  margin-top: 6px;
  font-size: 12.5px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  text-decoration: none;
}

/* History Cards */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}

.history-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 10px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.badge-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}

.badge-confirmed {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.badge-started {
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border-strong);
}

.source-badge {
  font-size: 11px;
  color: var(--text-muted);
}

.card-date {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.card-title {
  font-size: 14.5px;
  font-weight: 700;
  line-height: 1.4;
  margin: 0;
}

.title-link-btn {
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  font-size: inherit;
  font-weight: inherit;
  color: var(--text-primary);
  cursor: pointer;
  line-height: inherit;
}

.title-link-btn:hover {
  text-decoration: underline;
}

/* Verifiable Events Box */
.events-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  background-color: var(--bg-surface-elevated);
  border-radius: 8px;
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}

.event-icon {
  font-size: 14px;
  line-height: 1.2;
}

.event-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.event-name {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.event-time {
  font-size: 11px;
  color: var(--text-muted);
}

.event-detail {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 0;
}

.user-subtext {
  font-family: var(--font-mono);
  font-size: 10px;
}

/* OpenChat Verification Disclaimer */
.openchat-verification-notice {
  padding: 8px 10px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: 6px;
}

.notice-text {
  font-size: 10.5px;
  line-height: 1.45;
  color: var(--text-muted);
  margin: 0;
}

/* Actions */
.card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

.detail-action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
}

.confirm-action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
}

.confirm-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
