<script setup lang="ts">
import type { ScraperSchedule } from '@/services/api'
import TimePicker from '@/components/TimePicker.vue'

defineProps<{ disabled: boolean; schedule: ScraperSchedule | null }>()
const time = defineModel<string>('time', { required: true })
const timezone = defineModel<string>('timezone', { required: true })
const weekdays = defineModel<number[]>('weekdays', { required: true })
const dayLabels = ['월', '화', '수', '목', '금', '토', '일']
</script>

<template>
  <div class="english-schedule-fields">
    <p role="note">이 예약은 모든 English Scraper 등록에 공통 적용됩니다. Moatok에서 저장한 시각에 서버가 실행되며 앱을 닫아도 유지됩니다. 관리자 계정이 필요합니다.</p>
    <TimePicker v-model="time" id="english-scrape-time" label="수집 시각" :disabled="disabled" />
    <label for="scrape-timezone">시간대</label>
    <input id="scrape-timezone" v-model="timezone" class="form-input" placeholder="Asia/Seoul" :disabled="disabled" />
    <fieldset class="weekday-selector" :disabled="disabled">
      <legend class="weekday-selector-title">실행 요일</legend>
      <div class="weekday-options">
        <label v-for="(label, day) in dayLabels" :key="day" class="weekday-option">
          <input v-model="weekdays" class="weekday-checkbox" type="checkbox" :value="day" :aria-label="`${label}요일`" />
          <span class="weekday-button" aria-hidden="true">{{ label }}</span>
        </label>
      </div>
    </fieldset>
    <p v-if="schedule?.next_scheduled_at" role="status">다음 실행: {{ new Date(schedule.next_scheduled_at).toLocaleString('ko-KR', { timeZone: schedule.timezone }) }} ({{ schedule.timezone }})</p>
  </div>
</template>
