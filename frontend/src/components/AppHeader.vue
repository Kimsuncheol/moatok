<script setup lang="ts">
import { useMessagesStore } from '@/stores/messages'

const messagesStore = useMessagesStore()

function handleRefresh() {
  messagesStore.fetchAll(true)
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <div class="brand">
        <div class="brand-badge">MOATOK</div>
        <div class="brand-text">
          <h1 class="brand-title">모아톡</h1>
          <span class="brand-subtitle">카카오톡 공유 비서</span>
        </div>
      </div>

      <div class="header-actions">
        <button
          type="button"
          class="refresh-btn"
          :class="{ spinning: messagesStore.refreshing }"
          :disabled="messagesStore.refreshing"
          aria-label="새로고침"
          title="새로고침"
          @click="handleRefresh"
        >
          <svg class="refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  width: 100%;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  z-index: 40;
  padding-top: var(--sat);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  max-width: 480px;
  margin: 0 auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-badge {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.5px;
  padding: 4px 6px;
  border-radius: 4px;
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-primary);
  letter-spacing: -0.4px;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.2;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--text-secondary);
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  transition: all 0.15s ease;
}

.refresh-btn:hover {
  color: var(--text-primary);
  background-color: var(--bg-surface-hover);
}

.refresh-icon {
  width: 16px;
  height: 16px;
}

.refresh-btn.spinning .refresh-icon {
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
</style>
