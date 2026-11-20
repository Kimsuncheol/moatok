<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SettingsPage from '@/components/SettingsPage.vue'
import { englishScraperApi, type ScraperSchedule } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { englishScheduleTime, isEnglishEndpoint, useEndpointsStore } from '@/stores/endpoints'

const endpointsStore = useEndpointsStore()
const authStore = useAuthStore()
endpointsStore.loadEndpoints()

const selectedId = ref<string | null>(null)
const serverSchedule = ref<ScraperSchedule | null>(null)
const serverLoadFailed = ref(false)
const hasEnglishEndpoint = computed(() => endpointsStore.endpoints.some(isEnglishEndpoint))

watch([hasEnglishEndpoint, () => authStore.isLoading, () => authStore.isAdmin, () => authStore.userUid],
  async ([hasEnglish, authLoading, isAdmin], _, onCleanup) => {
    serverSchedule.value = null
    if (!hasEnglish || authLoading || !isAdmin) return

    let current = true
    onCleanup(() => { current = false })
    serverLoadFailed.value = false
    try {
      const schedule = await englishScraperApi.schedule()
      if (current) serverSchedule.value = schedule
    } catch {
      if (current) serverLoadFailed.value = true
    }
  }, { immediate: true })

const dayLabels = ['월', '화', '수', '목', '금', '토', '일']
const serverStatus = computed(() => {
  if (serverSchedule.value) return serverSchedule.value.enabled ? '활성' : '비활성'
  if (authStore.isLoading) return '확인 중'
  if (!authStore.isAdmin) return '관리자 확인 필요'
  return serverLoadFailed.value ? '확인 실패' : '확인 중'
})

function formatWeekdays(weekdays: number[] | undefined) {
  if (!weekdays || weekdays.length === dayLabels.length) return '매일'
  return dayLabels.filter((_, day) => weekdays.includes(day)).join(' · ')
}

const rows = computed(() => endpointsStore.endpoints
  .filter(endpoint => selectedId.value === null || endpoint.id === selectedId.value)
  .map(endpoint => {
    const isEnglish = isEnglishEndpoint(endpoint)
    const server = serverSchedule.value
    const local = endpoint.schedule
    const enabled = isEnglish ? server?.enabled : local.enabled
    const time = isEnglish ? (server && englishScheduleTime(server)) : local.scheduledTime
    const timezone = isEnglish ? server?.timezone : local.timezone
    const weekdays = isEnglish ? server?.weekdays : local.weekdays
    const nextRun = isEnglish ? server?.next_scheduled_at : local.nextRunAt

    return {
      id: endpoint.id,
      name: endpoint.name,
      time: enabled ? time : null,
      timezone,
      days: formatWeekdays(weekdays),
      nextRun: enabled && nextRun ? nextRun : null,
      nextRunLabel: enabled && nextRun
        ? new Date(nextRun).toLocaleString('ko-KR', { timeZone: timezone, dateStyle: 'medium', timeStyle: 'short' })
        : null,
      status: isEnglish ? serverStatus.value : (enabled ? '기기 설정' : '비활성')
    }
  }))
</script>

<template>
  <SettingsPage title="API 수집 일정" back-to="/registed_api" back-label="등록된 API 목록">
    <section class="api-schedules settings-card" aria-label="등록된 API 수집 일정">
      <div class="api-schedule-filters" role="group" aria-label="API 필터">
        <button type="button" :aria-pressed="selectedId === null" @click="selectedId = null">전체</button>
        <button v-for="endpoint in endpointsStore.endpoints" :key="endpoint.id" type="button"
          :aria-pressed="selectedId === endpoint.id" @click="selectedId = endpoint.id">
          {{ endpoint.name }}
        </button>
      </div>

      <p v-if="!rows.length" class="api-schedule-detail">등록된 API가 없습니다.</p>
      <table v-else class="api-schedule-table" aria-label="API별 수집 일정">
        <thead>
          <tr>
            <th scope="col">API</th>
            <th scope="col">수집 일정</th>
            <th scope="col">상태</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <th scope="row">{{ row.name }}</th>
            <td>
              <template v-if="row.time">
                <div>{{ row.days }} <time :datetime="row.time">{{ row.time }}</time></div>
                <div v-if="row.timezone" class="api-schedule-detail">{{ row.timezone }}</div>
                <div v-if="row.nextRun" class="api-schedule-detail">다음 실행 <time :datetime="row.nextRun">{{ row.nextRunLabel }}</time></div>
              </template>
              <template v-else>—</template>
            </td>
            <td>{{ row.status }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </SettingsPage>
</template>
