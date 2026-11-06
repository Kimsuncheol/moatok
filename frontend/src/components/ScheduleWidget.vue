<script setup lang="ts">
import { computed } from 'vue'
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

const isPM = computed(() => parsed.value.hour >= 12)
const displayHour12 = computed(() => {
  const h = parsed.value.hour % 12
  return h === 0 ? 12 : h
})
const displayPeriod = computed(() => (parsed.value.hour >= 12 ? 'PM' : 'AM'))

function updateHour(newHour: number) {
  const normalized = (newHour + 24) % 24
  emit('update:scheduledTime', formatTime(normalized, parsed.value.minute))
}

function updateMinute(newMinute: number) {
  const normalized = (newMinute + 60) % 60
  emit('update:scheduledTime', formatTime(parsed.value.hour, normalized))
}

function togglePeriod() {
  const current = parsed.value.hour
  if (current >= 12) {
    updateHour(current - 12)
  } else {
    updateHour(current + 12)
  }
}

function handleNativeTimeChange(e: Event) {
  const val = (e.target as HTMLInputElement).value
  if (val) {
    emit('update:scheduledTime', val)
  }
}

// Quick presets
const quickPresets = [
  { label: '🌅 아침 07:00', time: '07:00' },
  { label: '🏢 출근 09:00', time: '09:00' },
  { label: '🍽️ 점심 12:30', time: '12:30' },
  { label: '🌆 퇴근 18:00', time: '18:00' },
  { label: '🌙 밤 21:00', time: '21:00' }
]

const minuteOptions = [0, 15, 30, 45]

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

        <!-- Digital Clock & Stepper Controls -->
        <div class="digital-clock-controls">
          <!-- Hour Control -->
          <div class="stepper-unit">
            <button
              type="button"
              class="stepper-btn"
              aria-label="시간 증가"
              @click="updateHour(parsed.hour + 1)"
            >
              ▲
            </button>
            <div class="time-digit font-mono">{{ String(parsed.hour).padStart(2, '0') }}</div>
            <button
              type="button"
              class="stepper-btn"
              aria-label="시간 감소"
              @click="updateHour(parsed.hour - 1)"
            >
              ▼
            </button>
            <span class="unit-text">시 (Hour)</span>
          </div>

          <div class="clock-colon">:</div>

          <!-- Minute Control -->
          <div class="stepper-unit">
            <button
              type="button"
              class="stepper-btn"
              aria-label="분 5분 증가"
              @click="updateMinute(parsed.minute + 5)"
            >
              ▲
            </button>
            <div class="time-digit font-mono">{{ String(parsed.minute).padStart(2, '0') }}</div>
            <button
              type="button"
              class="stepper-btn"
              aria-label="분 5분 감소"
              @click="updateMinute(parsed.minute - 5)"
            >
              ▼
            </button>
            <span class="unit-text">분 (Min)</span>
          </div>

          <!-- AM/PM & 12h representation -->
          <div class="period-toggle-unit">
            <button
              type="button"
              class="period-badge-btn"
              :class="{ 'is-pm': isPM }"
              @click="togglePeriod"
              aria-label="오전/오후 전환"
            >
              {{ displayPeriod }}
            </button>
            <span class="period-sub font-mono">{{ displayHour12 }}:{{ String(parsed.minute).padStart(2, '0') }}</span>
          </div>
        </div>

        <!-- Quick Minute Chips -->
        <div class="minute-chips-row">
          <span class="chips-sub-label">분 단위:</span>
          <div class="chips-group">
            <button
              v-for="m in minuteOptions"
              :key="m"
              type="button"
              class="minute-chip"
              :class="{ active: parsed.minute === m }"
              @click="updateMinute(m)"
            >
              :{{ String(m).padStart(2, '0') }}분
            </button>
          </div>

          <!-- Native input fallback for direct mobile keyboards -->
          <label class="native-picker-wrapper" title="직접 시각 입력">
            <span class="native-picker-text">직접 입력:</span>
            <input
              type="time"
              :value="scheduledTime"
              class="native-time-field font-mono"
              @input="handleNativeTimeChange"
              aria-label="수집 시각 직접 입력"
            />
          </label>
        </div>
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

<style scoped>
/* Base Structure */
.schedule-widget {
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-radius: 12px;
  padding: 16px;
  transition: background-color 0.25s ease, border-color 0.25s ease, color 0.25s ease;
}

.schedule-widget.is-disabled {
  opacity: 0.45;
  pointer-events: none;
}

/* Light Theme Styling */
.schedule-widget.theme-light {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border-default, #dee2e6);
  color: var(--text-primary, #121212);
}

.schedule-widget.theme-light .time-picker-card,
.schedule-widget.theme-light .pipeline-card {
  background: var(--bg-surface-elevated, #f8f9fa);
  border: 1px solid var(--border-subtle, #e9ecef);
}

.schedule-widget.theme-light .stepper-unit {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border-default, #ced4da);
}

.schedule-widget.theme-light .stepper-btn {
  background: var(--bg-surface-elevated, #f1f3f5);
  color: var(--text-secondary, #495057);
}

.schedule-widget.theme-light .stepper-btn:hover {
  background: var(--bg-surface-hover, #e9ecef);
  color: var(--text-primary, #121212);
}

.schedule-widget.theme-light .minute-chip,
.schedule-widget.theme-light .preset-card-btn,
.schedule-widget.theme-light .ruler-slot-btn {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border-default, #dee2e6);
  color: var(--text-primary, #212529);
}

.schedule-widget.theme-light .minute-chip.active,
.schedule-widget.theme-light .preset-card-btn.active {
  background: var(--accent-action, #000000);
  color: var(--accent-action-text, #ffffff);
  border-color: var(--accent-action, #000000);
}

.schedule-widget.theme-light .ruler-slot-btn.is-scheduled {
  background: var(--accent-action, #000000);
  color: #ffffff;
  border-color: var(--accent-action, #000000);
}

.schedule-widget.theme-light .ruler-slot-btn.is-retry {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #92400e;
}

.schedule-widget.theme-light .pipeline-node {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border-subtle, #e9ecef);
}

.schedule-widget.theme-light .pipeline-node.node-initial {
  border-left: 3px solid #000000;
}

.schedule-widget.theme-light .pipeline-node.node-final {
  border-left: 3px solid #e11d48;
  background: #fff1f2;
}

/* Dark Theme Styling (OLED Contrast) */
.schedule-widget.theme-dark {
  background: var(--bg-surface, #0a0a0a);
  border: 1px solid var(--border-default, #2a2a2a);
  color: var(--text-primary, #f5f5f5);
}

.schedule-widget.theme-dark .time-picker-card,
.schedule-widget.theme-dark .pipeline-card {
  background: var(--bg-surface-elevated, #141414);
  border: 1px solid var(--border-subtle, #1c1c1c);
}

.schedule-widget.theme-dark .stepper-unit {
  background: #000000;
  border: 1px solid #333333;
}

.schedule-widget.theme-dark .stepper-btn {
  background: #1a1a1a;
  color: #a3a3a3;
}

.schedule-widget.theme-dark .stepper-btn:hover {
  background: #262626;
  color: #ffffff;
}

.schedule-widget.theme-dark .minute-chip,
.schedule-widget.theme-dark .preset-card-btn,
.schedule-widget.theme-dark .ruler-slot-btn {
  background: #000000;
  border: 1px solid #2a2a2a;
  color: #e5e5e5;
}

.schedule-widget.theme-dark .minute-chip.active,
.schedule-widget.theme-dark .preset-card-btn.active {
  background: #ffffff;
  color: #000000;
  border-color: #ffffff;
  font-weight: 700;
}

.schedule-widget.theme-dark .ruler-slot-btn.is-scheduled {
  background: #ffffff;
  color: #000000;
  border-color: #ffffff;
  font-weight: 700;
}

.schedule-widget.theme-dark .ruler-slot-btn.is-retry {
  background: #272005;
  border-color: #d97706;
  color: #fbbf24;
}

.schedule-widget.theme-dark .pipeline-node {
  background: #0a0a0a;
  border: 1px solid #222222;
}

.schedule-widget.theme-dark .pipeline-node.node-initial {
  border-left: 3px solid #ffffff;
}

.schedule-widget.theme-dark .pipeline-node.node-final {
  border-left: 3px solid #f43f5e;
  background: #21090f;
}

/* Header & Titles */
.widget-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.widget-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.98rem;
  font-weight: 700;
  margin: 0;
}

.clock-icon {
  width: 18px;
  height: 18px;
}

.theme-indicator-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 12px;
  background: rgba(128, 128, 128, 0.12);
  border: 1px solid rgba(128, 128, 128, 0.25);
  font-weight: 600;
}

.theme-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.widget-desc {
  font-size: 0.8rem;
  opacity: 0.75;
  margin: 0;
  line-height: 1.4;
}

/* Time Picker Card */
.time-picker-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border-radius: 10px;
}

.section-label {
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
}

/* Digital Clock */
.clock-display-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.digital-clock-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.stepper-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 8px;
  overflow: hidden;
  width: 72px;
}

.stepper-btn {
  width: 100%;
  padding: 4px 0;
  border: none;
  font-size: 0.7rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.time-digit {
  font-size: 1.9rem;
  font-weight: 800;
  padding: 4px 0;
  line-height: 1;
}

.unit-text {
  font-size: 0.65rem;
  opacity: 0.6;
  padding-bottom: 4px;
}

.clock-colon {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
  opacity: 0.5;
  margin-top: -16px;
}

.period-toggle-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
}

.period-badge-btn {
  font-size: 0.82rem;
  font-weight: 800;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid currentColor;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.period-sub {
  font-size: 0.72rem;
  opacity: 0.6;
}

/* Minute Chips Row */
.minute-chips-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}

.chips-sub-label {
  font-size: 0.75rem;
  opacity: 0.7;
  font-weight: 600;
}

.chips-group {
  display: flex;
  gap: 6px;
}

.minute-chip {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.native-picker-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
}

.native-picker-text {
  font-size: 0.72rem;
  opacity: 0.6;
}

.native-time-field {
  padding: 3px 6px;
  font-size: 0.75rem;
  border-radius: 4px;
  border: 1px solid rgba(128, 128, 128, 0.3);
  background: transparent;
  color: inherit;
}

/* Presets Section */
.presets-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(105px, 1fr));
  gap: 6px;
}

.preset-card-btn {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

/* 24-Hour Ruler */
.ruler-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ruler-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ruler-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.68rem;
  opacity: 0.8;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot-scheduled {
  background: currentColor;
}

.dot-retry {
  background: #f59e0b;
}

.ruler-bar-container {
  display: flex;
  overflow-x: auto;
  gap: 4px;
  padding: 6px 2px;
  scrollbar-width: thin;
}

.ruler-slot-btn {
  flex: 0 0 46px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 2px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.slot-icon {
  font-size: 0.7rem;
}

.slot-hour {
  font-size: 0.72rem;
  font-weight: 600;
}

.slot-badge {
  font-size: 0.58rem;
  padding: 1px 3px;
  border-radius: 3px;
  margin-top: 2px;
  font-weight: 800;
  background: rgba(0, 0, 0, 0.2);
}

/* Pipeline Card */
.pipeline-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border-radius: 10px;
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pipeline-title {
  font-size: 0.85rem;
}

.pipeline-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(128, 128, 128, 0.15);
  font-weight: 600;
}

.pipeline-nodes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pipeline-node {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.8rem;
  transition: transform 0.15s ease;
}

.node-time {
  font-size: 0.88rem;
  font-weight: 800;
  white-space: nowrap;
  min-width: 50px;
}

.node-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 4px;
}

.marker-circle {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.node-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-label-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.step-num {
  font-size: 0.68rem;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(128, 128, 128, 0.15);
  font-weight: 600;
}

.step-title {
  font-size: 0.82rem;
}

.step-subtext {
  font-size: 0.72rem;
  opacity: 0.75;
  margin: 0;
  line-height: 1.3;
}
</style>
