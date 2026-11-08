<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import { useThemeStore } from '@/stores/theme'
import type { AppearanceMode } from '@/types'
const themeStore = useThemeStore()
// Appearance modes list
interface AppearanceOption {
  mode: AppearanceMode
  name: string
  desc: string
  icon: string
}

const appearanceOptions: AppearanceOption[] = [
  {
    mode: 'system',
    name: '시스템 설정 (System)',
    desc: '기기 운영체제의 다크/라이트 모드 설정에 자동으로 동기화됩니다.',
    icon: '⚙️'
  },
  {
    mode: 'light',
    name: '라이트 모드 (Light)',
    desc: '밝고 선명한 단색 고대비 모노크롬 테마입니다.',
    icon: '☀️'
  },
  {
    mode: 'dark',
    name: '다크 모드 (Dark)',
    desc: '눈의 피로를 줄이고 배터리를 절약하는 트루 블랙 OLED 최적화 테마입니다.',
    icon: '🌙'
  }
]

</script>
<template>
  <SettingsPage title="화면 테마">
<!-- 1. Appearance Modes as a List (NO dropdown!) -->
    <section class="settings-card" aria-labelledby="appearance-heading">
      <div class="card-title-row">
        <h3 id="appearance-heading" class="card-title">화면 테마 모드 (Appearance)</h3>
        <span class="info-badge">모노크롬 테마</span>
      </div>
      <p class="setting-caption">
        시스템 설정에 맞추거나 라이트/다크 모드를 목록에서 선택하여 전환합니다.
      </p>

      <ul class="appearance-mode-list" role="radiogroup" aria-label="화면 테마 모드 목록">
        <li
          v-for="item in appearanceOptions"
          :key="item.mode"
          class="appearance-mode-item"
          :class="{ selected: themeStore.mode === item.mode }"
          role="radio"
          :aria-checked="themeStore.mode === item.mode"
          tabindex="0"
          @click="themeStore.setMode(item.mode)"
          @keydown.space.prevent="themeStore.setMode(item.mode)"
          @keydown.enter.prevent="themeStore.setMode(item.mode)"
        >
          <div class="mode-info">
            <div class="mode-title-row">
              <span class="mode-icon" aria-hidden="true">{{ item.icon }}</span>
              <strong class="mode-name">{{ item.name }}</strong>
              <span v-if="themeStore.mode === item.mode" class="current-badge">적용 중</span>
            </div>
            <p class="mode-desc">{{ item.desc }}</p>
          </div>
          <div class="mode-radio-indicator" aria-hidden="true">
            <span v-if="themeStore.mode === item.mode" class="radio-dot" />
          </div>
        </li>
      </ul>
    </section>

      </SettingsPage>
</template>
