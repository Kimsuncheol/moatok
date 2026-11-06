<script setup lang="ts">
import 'temporal-polyfill/global'
import { Temporal } from 'temporal-polyfill'
import { ref, computed, watch, onMounted, shallowRef } from 'vue'
import { ScheduleXCalendar } from '@schedule-x/vue'
import {
  createCalendar,
  viewDay,
  viewWeek,
  viewMonthAgenda
} from '@schedule-x/calendar'
import '@schedule-x/theme-default/dist/index.css'

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

const calendarApp = shallowRef<any>(null)
const isCalendarReady = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const quickPresets = [
  { label: '아침 07:00', time: '07:00' },
  { label: '오전 09:00', time: '09:00' },
  { label: '점심 12:30', time: '12:30' },
  { label: '저녁 18:00', time: '18:00' },
  { label: '밤 21:00', time: '21:00' }
]

function parseTime(timeStr: string) {
  const [h, m] = (timeStr || '09:00').split(':').map((n) => parseInt(n, 10))
  return {
    hour: isNaN(h) ? 9 : Math.min(Math.max(h, 0), 23),
    minute: isNaN(m) ? 0 : Math.min(Math.max(m, 0), 59)
  }
}

function formatTimeString(hour: number, minute: number): string {
  const hh = String(hour).padStart(2, '0')
  const mm = String(minute).padStart(2, '0')
  return `${hh}:${mm}`
}

const scheduleTimeline = computed(() => {
  const { hour, minute } = parseTime(props.scheduledTime)
  const steps = []

  for (let attempt = 1; attempt <= 5; attempt++) {
    const attemptHour = (hour + (attempt - 1)) % 24
    const timeFormatted = formatTimeString(attemptHour, minute)
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

function buildCalendarEvents() {
  const today = Temporal.Now.plainDateISO()
  const timeZone = Temporal.Now.timeZoneId()
  const { hour, minute } = parseTime(props.scheduledTime)

  return scheduleTimeline.value.map((step) => {
    const attemptHour = (hour + (step.attempt - 1)) % 24
    // If wrapped to next day, handle date offset
    const dayOffset = Math.floor((hour + (step.attempt - 1)) / 24)
    const targetDate = dayOffset > 0 ? today.add({ days: dayOffset }) : today

    const start = targetDate.toZonedDateTime({
      plainTime: { hour: attemptHour, minute },
      timeZone
    })
    const end = start.add({ minutes: 30 })

    return {
      id: `fetch-slot-${step.attempt}`,
      title: `[${step.time}] ${step.label} (${props.endpointName || 'API'})`,
      start,
      end
    }
  })
}

function initCalendar() {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return
  }

  try {
    const today = Temporal.Now.plainDateISO()
    const events = buildCalendarEvents()

    calendarApp.value = createCalendar({
      views: [viewDay, viewWeek, viewMonthAgenda],
      defaultView: viewDay.name,
      selectedDate: today,
      events
    })
    isCalendarReady.value = true
  } catch (err) {
    console.error('Failed to initialize Schedule-X calendar:', err)
  }
}

function updateCalendarEvents() {
  if (!calendarApp.value || !calendarApp.value.events) return
  try {
    const events = buildCalendarEvents()
    calendarApp.value.events.set(events)
  } catch (err) {
    console.error('Failed to update calendar events:', err)
  }
}

function handleSelectPreset(time: string) {
  emit('update:scheduledTime', time)
}

watch(
  () => [props.scheduledTime, props.endpointName],
  () => {
    updateCalendarEvents()
  }
)

onMounted(() => {
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    if (containerRef.value && (containerRef.value.isConnected || document.body.contains(containerRef.value))) {
      initCalendar()
    }
  }
})
</script>

<template>
  <div
    ref="containerRef"
    class="schedule-widget-container"
    :class="{ 'is-disabled': !enabled }"
  >
    <div class="widget-header">
      <div class="header-titles">
        <h4 class="widget-title">
          <svg class="calendar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          Schedule-X 일정 시각화
        </h4>
        <span class="widget-badge">Schedule-X v4</span>
      </div>
      <p class="widget-caption">
        설정된 시각 기준 1차 시도 및 실패 시 1시간 간격으로 최대 5회 재시도 일정이 캘린더에 자동 반영됩니다.
      </p>
    </div>

    <!-- Quick Time Preset Chips -->
    <div class="preset-chips-row" role="group" aria-label="빠른 시각 선택">
      <span class="chips-label">빠른 선택:</span>
      <div class="chips-list">
        <button
          v-for="preset in quickPresets"
          :key="preset.time"
          type="button"
          class="preset-chip"
          :class="{ active: scheduledTime === preset.time }"
          @click="handleSelectPreset(preset.time)"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>

    <!-- Schedule-X Interactive Calendar View -->
    <div class="calendar-card">
      <div class="calendar-view-header">
        <span class="view-indicator">일별 / 주별 수집 타임라인</span>
        <span class="current-selected-time">기준 시각: <strong>{{ scheduledTime }}</strong></span>
      </div>

      <div v-if="isCalendarReady && calendarApp" class="sx-wrapper">
        <ScheduleXCalendar :calendar-app="calendarApp" />
      </div>
      <div v-else class="calendar-loading-fallback">
        <span>캘린더 로딩 중...</span>
      </div>
    </div>

    <!-- Step-by-Step 5 Attempt Policy Summary Timeline -->
    <div class="attempts-timeline" aria-label="5회 재시도 상세 일정">
      <div
        v-for="step in scheduleTimeline"
        :key="step.attempt"
        class="timeline-node"
        :class="{ 'first-node': step.isFirst, 'last-node': step.isLast }"
      >
        <div class="node-time-badge font-mono">{{ step.time }}</div>
        <div class="node-info">
          <div class="node-title-row">
            <span class="node-number">{{ step.attempt }}회차</span>
            <strong class="node-label">{{ step.label }}</strong>
          </div>
          <span class="node-desc">{{ step.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.schedule-widget-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--color-bg-card, #ffffff);
  border: 1px solid var(--color-border, #e5e5e5);
  border-radius: 12px;
  padding: 16px;
  margin-top: 14px;
  transition: opacity 0.2s ease;
}

.schedule-widget-container.is-disabled {
  opacity: 0.5;
  pointer-events: none;
}

.widget-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-titles {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.widget-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text-primary, #111111);
  margin: 0;
}

.calendar-icon {
  width: 18px;
  height: 18px;
  stroke: currentColor;
}

.widget-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-bg-secondary, #f3f3f3);
  color: var(--color-text-secondary, #666666);
  border: 1px solid var(--color-border, #e5e5e5);
  font-weight: 600;
}

.widget-caption {
  font-size: 0.78rem;
  color: var(--color-text-secondary, #666666);
  margin: 0;
  line-height: 1.4;
}

/* Quick Presets */
.preset-chips-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chips-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text-secondary, #555555);
}

.chips-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preset-chip {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid var(--color-border, #dddddd);
  background: var(--color-bg-card, #ffffff);
  color: var(--color-text-primary, #222222);
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-chip:hover {
  background: var(--color-bg-secondary, #f0f0f0);
}

.preset-chip.active {
  background: var(--color-text-primary, #000000);
  color: var(--color-bg-primary, #ffffff);
  border-color: var(--color-text-primary, #000000);
  font-weight: 700;
}

/* Calendar Card */
.calendar-card {
  border: 1px solid var(--color-border, #e5e5e5);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-card, #ffffff);
}

.calendar-view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--color-bg-secondary, #f9f9f9);
  border-bottom: 1px solid var(--color-border, #e5e5e5);
  font-size: 0.78rem;
  color: var(--color-text-secondary, #666666);
}

.current-selected-time strong {
  color: var(--color-text-primary, #111111);
}

.sx-wrapper {
  min-height: 340px;
  max-height: 480px;
  overflow-y: auto;
  position: relative;
}

.calendar-loading-fallback {
  padding: 40px 16px;
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-text-secondary, #888888);
}

/* Attempts Timeline */
.attempts-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.timeline-node {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-bg-secondary, #fafafa);
  border: 1px solid var(--color-border, #eeeeee);
  font-size: 0.8rem;
}

.timeline-node.first-node {
  border-left: 3px solid var(--color-text-primary, #000000);
}

.timeline-node.last-node {
  border-left: 3px solid #e11d48;
  background: rgba(225, 29, 72, 0.04);
}

.node-time-badge {
  font-size: 0.85rem;
  font-weight: 700;
  padding: 2px 6px;
  background: var(--color-bg-card, #ffffff);
  border: 1px solid var(--color-border, #cccccc);
  border-radius: 4px;
  color: var(--color-text-primary, #111111);
  white-space: nowrap;
}

.node-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-number {
  font-size: 0.7rem;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--color-bg-card, #ffffff);
  border: 1px solid var(--color-border, #e0e0e0);
  color: var(--color-text-secondary, #666666);
}

.node-label {
  font-size: 0.8rem;
  color: var(--color-text-primary, #111111);
}

.node-desc {
  font-size: 0.72rem;
  color: var(--color-text-secondary, #777777);
  line-height: 1.3;
}

/* Dark mode overrides */
:global(.dark) .schedule-widget-container,
:global([data-theme='dark']) .schedule-widget-container {
  background: #0d0d0d;
  border-color: #222222;
}

:global(.dark) .widget-title,
:global([data-theme='dark']) .widget-title {
  color: #ffffff;
}

:global(.dark) .widget-badge,
:global([data-theme='dark']) .widget-badge {
  background: #1a1a1a;
  border-color: #333333;
  color: #aaaaaa;
}

:global(.dark) .preset-chip,
:global([data-theme='dark']) .preset-chip {
  background: #161616;
  border-color: #333333;
  color: #e0e0e0;
}

:global(.dark) .preset-chip.active,
:global([data-theme='dark']) .preset-chip.active {
  background: #ffffff;
  color: #000000;
  border-color: #ffffff;
}

:global(.dark) .calendar-card,
:global([data-theme='dark']) .calendar-card {
  background: #111111;
  border-color: #222222;
}

:global(.dark) .calendar-view-header,
:global([data-theme='dark']) .calendar-view-header {
  background: #181818;
  border-color: #262626;
  color: #aaaaaa;
}

:global(.dark) .timeline-node,
:global([data-theme='dark']) .timeline-node {
  background: #141414;
  border-color: #242424;
}

:global(.dark) .node-time-badge,
:global([data-theme='dark']) .node-time-badge {
  background: #202020;
  border-color: #333333;
  color: #ffffff;
}

:global(.dark) .node-title-row strong,
:global([data-theme='dark']) .node-title-row strong {
  color: #ffffff;
}

/* Custom styling for Schedule-X inside Moatok monochrome UI */
:deep(.sx__calendar) {
  font-family: inherit;
}

:deep(.sx__date-grid-event),
:deep(.sx__time-grid-event) {
  background-color: #111111 !important;
  color: #ffffff !important;
  border-left: 3px solid #ffffff !important;
}

:global(.dark) :deep(.sx__date-grid-event),
:global(.dark) :deep(.sx__time-grid-event),
:global([data-theme='dark']) :deep(.sx__date-grid-event),
:global([data-theme='dark']) :deep(.sx__time-grid-event) {
  background-color: #262626 !important;
  color: #ffffff !important;
  border-left: 3px solid #60a5fa !important;
}
</style>
