<script setup lang="ts">
import { computed, useId } from 'vue'
import TimePicker from '@/components/TimePicker.vue'
const pickerId = useId()
import { useThemeStore } from '@/stores/theme'

interface Props {
  scheduledTime?: string
  endpointName?: string
  enabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  scheduledTime: '09:00',
  endpointName: 'API Endpoint',
  enabled: true
})

const emit = defineEmits<{
  (e: 'update:scheduledTime', value: string): void
}>()

const themeStore = useThemeStore()

// React to appearance mode (light / dark / system)
const isDarkMode = computed(() => themeStore.resolvedTheme === 'dark')

const currentThemeLabel = computed(() => {
  if (themeStore.mode === 'system') {
    return isDarkMode.value ? '다크 모드 (시스템 연동)' : '라이트 모드 (시스템 연동)'
  }
  return isDarkMode.value ? '다크 모드' : '라이트 모드'
})

// Parse HH:mm
function parseTime(timeStr: string) {
  const parts = (timeStr || '09:00').split(':')
  let h = parseInt(parts[0], 10)
  let m = parseInt(parts[1], 10)
  if (isNaN(h)) h = 9
  if (isNaN(m)) m = 0
  h = Math.min(Math.max(h, 0), 23)
  m = Math.min(Math.max(m, 0), 59)
  return { hour: h, minute: m }
}

function formatTime(hour: number, minute: number): string {
  const hh = String(hour).padStart(2, '0')
  const mm = String(minute).padStart(2, '0')
  return `${hh}:${mm}`
}

const parsed = computed(() => parseTime(props.scheduledTime))

function updateHour(newHour: number) {
  const normalized = (newHour + 24) % 24
  emit('update:scheduledTime', formatTime(normalized, parsed.value.minute))
}

// Quick presets
const quickPresets = [
  { label: '🌅 아침 07:00', time: '07:00' },
  { label: '🏢 출근 09:00', time: '09:00' },
  { label: '🍽️ 점심 12:30', time: '12:30' },
  { label: '🌆 퇴근 18:00', time: '18:00' },
  { label: '🌙 밤 21:00', time: '21:00' }
]


// 24-hour slots with 5-attempt calculation
const hours24 = computed(() => {
  const scheduledHour = parsed.value.hour
  const slots = []

  for (let h = 0; h < 24; h++) {
    // Check if this hour matches one of the 5 attempts
    let attemptNumber: number | null = null
    for (let i = 0; i < 5; i++) {
      if ((scheduledHour + i) % 24 === h) {
        attemptNumber = i + 1
        break
      }
    }

    const isDaytime = h >= 6 && h < 18
    slots.push({
      hour: h,
      label: `${String(h).padStart(2, '0')}:00`,
      displayH: `${h}시`,
      isDaytime,
      isScheduled: attemptNumber === 1,
      attemptNumber,
      isRetry: attemptNumber !== null && attemptNumber > 1
    })
  }
  return slots
})

// 5-Attempt Detailed Timeline
const scheduleTimeline = computed(() => {
  const { hour, minute } = parsed.value
  const steps = []

  for (let attempt = 1; attempt <= 5; attempt++) {
    const attemptHour = (hour + (attempt - 1)) % 24
    const timeFormatted = formatTime(attemptHour, minute)
    const isFirst = attempt === 1
    const isLast = attempt === 5

    let label = ''
    let description = ''
    if (isFirst) {
      label = '1차 자동 수집'
      description = '정기 스케줄 실행'
    } else if (isLast) {
      label = `5차 최종 재시도 (+${attempt - 1}h)`
      description = '실패 시 Pending 뷰에 Fetch 버튼 제공'
    } else {
      label = `${attempt}차 재시도 (+${attempt - 1}h)`
      description = '1차 실패 후 1시간 뒤 재시도'
    }

    steps.push({
      attempt,
      time: timeFormatted,
      label,
      description,
      isFirst,
      isLast
    })
  }
  return steps
})

function selectHourFromBar(h: number) {
  updateHour(h)
}
</script>

<template>
  <div
    class="schedule-widget"
    :class="[
      isDarkMode ? 'theme-dark' : 'theme-light',
      { 'is-disabled': !enabled }
    ]"
    role="region"
    aria-label="API 수집 시각 및 스케줄 설정"
  >
    <!-- Widget Header with Appearance Mode Badge -->
    <div class="widget-header">
      <div class="title-row">
        <h4 class="widget-heading">
          <svg class="clock-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          수집 시각 선택 (What time)
        </h4>
        <div class="theme-indicator-badge" :title="`현재 테마: ${currentThemeLabel}`">
          <span class="theme-dot"></span>
          <span class="theme-label">{{ currentThemeLabel }}</span>
        </div>
      </div>
      <p class="widget-desc">
        매일 자동으로 API 데이터를 가져올 시각을 선택하세요. 실패 시 1시간 간격으로 최대 5회 자동 재시도됩니다.
      </p>
    </div>

    <!-- Main Time Picker Card -->
    <div class="time-picker-card">
      <div class="clock-display-section">
        <span class="section-label">선택된 수집 시각</span>

        <TimePicker :id="pickerId" :model-value="scheduledTime" label="수집 시각" :disabled="!enabled" @update:model-value="emit('update:scheduledTime', $event)" />
      </div>

      <!-- Quick Preset Buttons -->
      <div class="presets-section">
        <span class="section-label">자주 사용하는 시간</span>
        <div class="presets-grid" role="group" aria-label="추천 시간 프리셋">
          <button
            v-for="preset in quickPresets"
            :key="preset.time"
            type="button"
            class="preset-card-btn"
            :class="{ active: scheduledTime === preset.time }"
            @click="emit('update:scheduledTime', preset.time)"
          >
            <span class="preset-name">{{ preset.label }}</span>
          </button>
        </div>
      </div>

      <!-- 24-Hour Interactive Visual Ruler -->
      <div class="ruler-section">
        <div class="ruler-header">
          <span class="section-label">24시간 타임라인에서 시간 클릭</span>
          <span class="ruler-legend">
            <span class="legend-item"><span class="legend-dot dot-scheduled"></span>1차 실행</span>
            <span class="legend-item"><span class="legend-dot dot-retry"></span>재시도(2~5차)</span>
          </span>
        </div>

        <div class="ruler-bar-container" role="listbox" aria-label="24시간 슬롯 선택">
          <button
            v-for="slot in hours24"
            :key="slot.hour"
            type="button"
            class="ruler-slot-btn"
            :class="{
              'is-scheduled': slot.isScheduled,
              'is-retry': slot.isRetry,
              'is-day': slot.isDaytime,
              'is-night': !slot.isDaytime
            }"
            :aria-selected="slot.isScheduled"
            :title="`${slot.label} 선택`"
            @click="selectHourFromBar(slot.hour)"
          >
            <span class="slot-icon">{{ slot.isDaytime ? '☀️' : '🌙' }}</span>
            <span class="slot-hour font-mono">{{ slot.displayH }}</span>
            <span v-if="slot.attemptNumber" class="slot-badge">
              {{ slot.attemptNumber === 1 ? '1차' : `${slot.attemptNumber}차` }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- 5-Attempt Execution Pipeline Timeline -->
    <div class="pipeline-card" aria-label="5회 재시도 자동 실행 타임라인">
      <div class="pipeline-header">
        <strong class="pipeline-title">⚡ 수집 및 5회 재시도 타임라인</strong>
        <span class="pipeline-badge">최대 5회 (1시간 간격)</span>
      </div>

      <div class="pipeline-nodes-list">
        <div
          v-for="step in scheduleTimeline"
          :key="step.attempt"
          class="pipeline-node"
          :class="{ 'node-initial': step.isFirst, 'node-final': step.isLast }"
        >
          <div class="node-time font-mono">{{ step.time }}</div>
          <div class="node-marker">
            <span class="marker-circle"></span>
            <span v-if="!step.isLast" class="marker-line"></span>
          </div>
          <div class="node-content">
            <div class="node-label-row">
              <span class="step-num">{{ step.attempt }}회차</span>
              <strong class="step-title">{{ step.label }}</strong>
            </div>
            <p class="step-subtext">{{ step.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
