<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import type { AppearanceMode } from '@/types'

const themeStore = useThemeStore()

const options: { value: AppearanceMode; label: string; icon: string }[] = [
  { value: 'system', label: '시스템', icon: '💻' },
  { value: 'light', label: '라이트', icon: '☀️' },
  { value: 'dark', label: '다크', icon: '🌙' }
]

function selectMode(mode: AppearanceMode) {
  themeStore.setMode(mode)
}
</script>

<template>
  <div class="appearance-segmented-control" role="radiogroup" aria-label="화면 모드 선택">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      role="radio"
      :aria-checked="themeStore.mode === opt.value"
      class="segment-btn"
      :class="{ active: themeStore.mode === opt.value }"
      @click="selectMode(opt.value)"
    >
      <span class="icon">{{ opt.icon }}</span>
      <span class="label">{{ opt.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.appearance-segmented-control {
  display: flex;
  align-items: center;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
  width: 100%;
}

.segment-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  transition: all 0.15s ease;
}

.segment-btn:hover {
  color: var(--text-primary);
  background-color: var(--bg-surface-hover);
}

.segment-btn.active {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.icon {
  font-size: 13px;
  line-height: 1;
}

.label {
  letter-spacing: -0.2px;
}
</style>
