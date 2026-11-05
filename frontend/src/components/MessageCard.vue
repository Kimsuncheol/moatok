<script setup lang="ts">
import { computed } from 'vue'
import type { ShareMessage } from '@/types'

const props = defineProps<{
  message: ShareMessage
}>()

const emit = defineEmits<{
  (e: 'select', message: ShareMessage): void
  (e: 'review', message: ShareMessage): void
}>()

function extractDomain(url?: string): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

const isPending = computed(() => props.message.status === 'pending' || !props.message.kakao_shared)

const sourceName = computed(() => {
  return (
    props.message.source_name ||
    props.message.items?.[0]?.source_name ||
    extractDomain(props.message.target_url) ||
    '출처 미정'
  )
})

const statusLabel = computed(() => {
  if (props.message.kakao_shared) return '카카오톡 공유됨'
  switch (props.message.status) {
    case 'shared':
    case 'shared_by_user':
      return '카카오톡 공유됨'
    case 'notified':
      return '알림 발송됨'
    case 'failed':
      return '실패'
    case 'archived':
      return '보관됨'
    case 'pending':
    default:
      return '공유 대기'
  }
})

const formattedCreationTime = computed(() => {
  const dateStr = props.message.created_at
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const now = Date.now()
    const diffMs = now - d.getTime()
    const diffMin = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMin < 1) return '방금 전'
    if (diffMin < 60) return `${diffMin}분 전`
    if (diffHours < 24) return `${diffHours}시간 전`
    if (diffDays < 7) return `${diffDays}일 전`

    return new Intl.DateTimeFormat('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  } catch {
    return dateStr
  }
})

function handleCardClick() {
  emit('select', props.message)
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('select', props.message)
  }
}

function handleReviewClick(e: Event) {
  e.stopPropagation()
  emit('review', props.message)
}
</script>

<template>
  <article
    class="message-card"
    :class="{ 'is-pending': isPending }"
    tabindex="0"
    role="article"
    :aria-label="`${message.title} (${sourceName}, ${statusLabel})`"
    @click="handleCardClick"
    @keydown="handleKeyDown"
  >
    <!-- Header with Status, Source, and Creation Time -->
    <header class="card-header">
      <div class="status-container">
        <span
          class="status-badge"
          :class="isPending ? 'badge-pending' : 'badge-shared'"
          :aria-label="`상태: ${statusLabel}`"
        >
          {{ statusLabel }}
        </span>

        <span
          class="source-badge"
          :title="`출처: ${sourceName}`"
          :aria-label="`출처: ${sourceName}`"
        >
          <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          <span class="source-text">{{ sourceName }}</span>
        </span>
      </div>

      <time
        class="card-time"
        :datetime="message.created_at"
        :title="`작성 일시: ${message.created_at}`"
      >
        {{ formattedCreationTime }}
      </time>
    </header>

    <!-- Title -->
    <h2 class="card-title">{{ message.title }}</h2>

    <!-- Excerpt / Body -->
    <p class="card-body">{{ message.body }}</p>

    <!-- Source URL Link -->
    <div v-if="message.target_url" class="card-target-url" @click.stop>
      <span class="url-label" aria-hidden="true">🔗 원문:</span>
      <a
        :href="message.target_url"
        target="_blank"
        rel="noopener noreferrer"
        class="url-link"
        :aria-label="`${message.title} 원문 링크 열기 (새 창)`"
      >
        {{ message.target_url }}
      </a>
    </div>

    <!-- Actions Footer -->
    <footer class="card-footer">
      <button
        type="button"
        class="action-btn select-detail-btn"
        :aria-label="`${message.title} 상세 보기`"
        @click.stop="handleCardClick"
      >
        <span>상세 보기</span>
        <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

      <button
        type="button"
        class="action-btn quick-share-btn"
        :class="isPending ? 'btn-primary' : 'btn-secondary'"
        :aria-label="isPending ? `${message.title} 검토 및 카카오톡 공유` : `${message.title} 내용 다시보기`"
        @click="handleReviewClick"
      >
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
        <span>{{ isPending ? '카카오톡 공유' : '공유 완료' }}</span>
      </button>
    </footer>
  </article>
</template>

<style scoped>
.message-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  outline: none;
}

.message-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

.message-card:focus-visible {
  border-color: var(--accent-action);
  box-shadow: 0 0 0 2px var(--border-strong);
}

.message-card.is-pending {
  border-left: 4px solid var(--accent-action);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.status-container {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: -0.2px;
}

.badge-pending {
  background-color: var(--badge-pending-bg);
  color: var(--badge-pending-text);
}

.badge-shared {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
  max-width: 150px;
}

.meta-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.source-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-time {
  font-size: 11.5px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.card-body {
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--text-secondary);
  white-space: pre-line;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-target-url {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-muted);
  overflow: hidden;
}

.url-label {
  flex-shrink: 0;
}

.url-link {
  color: var(--text-secondary);
  text-decoration: underline;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-link:hover {
  color: var(--text-primary);
}

.card-footer {
  margin-top: 4px;
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  min-height: 44px; /* Accessible mobile touch target */
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.select-detail-btn {
  background-color: var(--bg-surface-elevated);
  border-color: var(--border-default);
  color: var(--text-primary);
}

.select-detail-btn:hover {
  border-color: var(--border-strong);
}

.chevron-icon {
  width: 14px;
  height: 14px;
}

.btn-primary {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.btn-primary:hover {
  background-color: var(--accent-action-hover);
}

.btn-secondary {
  background-color: var(--bg-surface-elevated);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  border-color: var(--border-strong);
}

.btn-icon {
  width: 14px;
  height: 14px;
}
</style>
