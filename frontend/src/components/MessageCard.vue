<script setup lang="ts">
import { computed } from 'vue'
import type { ShareMessage } from '@/types'

const props = defineProps<{
  message: ShareMessage
}>()

const emit = defineEmits<{
  (e: 'review', message: ShareMessage): void
}>()

const isPending = computed(() => props.message.status === 'pending' || !props.message.kakao_shared)

const formattedDate = computed(() => {
  const dateStr = props.message.shared_by_user_at || props.message.created_at
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
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
</script>

<template>
  <article class="message-card" :class="{ 'is-pending': isPending }">
    <div class="card-header">
      <div class="status-container">
        <span class="status-badge" :class="isPending ? 'badge-pending' : 'badge-shared'">
          {{ isPending ? '공유 대기' : '카카오톡 공유됨' }}
        </span>
        <span v-if="message.last_share_channel" class="channel-tag">
          {{ message.last_share_channel === 'kakao_sdk' ? 'Kakao SDK' : message.last_share_channel }}
        </span>
      </div>
      <time class="card-time">{{ formattedDate }}</time>
    </div>

    <h2 class="card-title">{{ message.title }}</h2>

    <p class="card-body">{{ message.body }}</p>

    <div v-if="message.target_url" class="card-target-url">
      <span class="url-label">🔗 원문:</span>
      <a :href="message.target_url" target="_blank" rel="noopener noreferrer" class="url-link">
        {{ message.target_url }}
      </a>
    </div>

    <div class="card-footer">
      <button
        type="button"
        class="action-btn"
        :class="isPending ? 'btn-primary' : 'btn-secondary'"
        @click="emit('review', message)"
      >
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
        <span>{{ isPending ? '검토 및 카카오톡 공유' : '내용 다시보기' }}</span>
      </button>
    </div>
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
  transition: border-color 0.15s ease;
}

.message-card:hover {
  border-color: var(--border-strong);
}

.message-card.is-pending {
  border-left: 3px solid var(--accent-action);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-container {
  display: flex;
  align-items: center;
  gap: 6px;
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

.channel-tag {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
}

.card-time {
  font-size: 12px;
  color: var(--text-muted);
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
  -webkit-line-clamp: 4;
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

.card-footer {
  margin-top: 4px;
}

.action-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 600;
  transition: all 0.15s ease;
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
  border: 1px solid var(--border-default);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background-color: var(--bg-surface-hover);
}

.btn-icon {
  width: 16px;
  height: 16px;
}
</style>
