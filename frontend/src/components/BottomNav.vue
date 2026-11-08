<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useMessagesStore } from '@/stores/messages'

const route = useRoute()
const messagesStore = useMessagesStore()

const pendingCount = computed(() => messagesStore.pendingCount)
const historyCount = computed(() => messagesStore.historyCount)

const navItems = computed(() => [
  {
    name: 'pending',
    path: '/',
    label: 'Pending',
    sublabel: '대기중',
    badge: pendingCount.value,
    badgeClass: 'pending-badge'
  },
  {
    name: 'history',
    path: '/history',
    label: 'History',
    sublabel: '공유이력',
    badge: historyCount.value > 0 ? historyCount.value : null,
    badgeClass: 'history-badge'
  },
  {
    name: 'settings',
    path: '/settings',
    label: 'Settings',
    sublabel: '설정',
    badge: null,
    badgeClass: ''
  }
])
</script>

<template>
  <nav class="bottom-nav" aria-label="하단 내비게이션">
    <RouterLink
      v-for="item in navItems"
      :key="item.name"
      :to="item.path"
      class="nav-tab"
      :class="{ active: (route.name === item.name || (item.name === 'settings' && (route.path?.startsWith('/settings/') || route.name === 'register-api'))) }"
      :aria-current="(route.name === item.name || (item.name === 'settings' && (route.path?.startsWith('/settings/') || route.name === 'register-api'))) ? 'page' : undefined"
    >
      <div class="icon-wrapper">
        <!-- Minimalist Monochrome SVG Icons -->
        <svg v-if="item.name === 'pending'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        <svg v-else-if="item.name === 'history'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          <polyline points="10 8 13 11 17 7" />
        </svg>
        <svg v-else-if="item.name === 'settings'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>

        <span v-if="item.badge !== null && item.badge > 0" class="nav-badge" :class="item.badgeClass">
          {{ item.badge > 99 ? '99+' : item.badge }}
        </span>
      </div>
      <span class="nav-label">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding-top: 8px;
  padding-bottom: calc(8px + var(--sab));
  z-index: 50;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.nav-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: var(--text-muted);
  text-decoration: none;
  padding: 4px 0;
  transition: color 0.15s ease;
}

.nav-tab:hover {
  color: var(--text-secondary);
}

.nav-tab.active {
  color: var(--accent-action);
}

.icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon {
  width: 22px;
  height: 22px;
  stroke: currentColor;
}

.nav-badge {
  position: absolute;
  top: -4px;
  right: -10px;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 999px;
  min-width: 16px;
  text-align: center;
  line-height: 1.2;
}

.pending-badge {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.history-badge {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.nav-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: -0.2px;
}

.nav-tab.active .nav-label {
  font-weight: 700;
}
</style>
