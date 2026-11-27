<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsPage from '@/components/SettingsPage.vue'
import EnglishScheduleFields from '@/components/EnglishScheduleFields.vue'
import { englishScraperApi, type ScraperSchedule } from '@/services/api'
import { useEndpointsStore, englishScheduleTime, isEnglishEndpoint, type EnglishScheduleDraft } from '@/stores/endpoints'
import type { ApiEndpoint, ApiSchedule } from '@/types'

const endpointsStore = useEndpointsStore()
onMounted(() => endpointsStore.loadEndpoints())

const actionFeedback = ref('')
const editingId = ref<string | null>(null)
const scheduleBusy = ref(false)
const draft = ref<EnglishScheduleDraft | null>(null)
const cloudSchedule = ref<ScraperSchedule | null>(null)

function collectionStatus(ep: ApiEndpoint): ApiSchedule['lastStatus'] {
  if (endpointsStore.isFetching(ep.id)) return 'fetching'
  return ep.schedule.lastStatus === 'fetching' ? 'idle' : ep.schedule.lastStatus
}

function scheduleLabel(ep: ApiEndpoint) {
  if (!isEnglishEndpoint(ep)) return ep.schedule.enabled ? `매일 ${ep.schedule.scheduledTime}` : '비활성'
  const schedule = cloudSchedule.value
  if (!schedule) return '서버 예약 변경에서 현재 시각 확인'
  return schedule.enabled ? `${englishScheduleTime(schedule)} (${schedule.timezone})` : '서버 예약 비활성'
}

async function editSchedule(id: string) {
  scheduleBusy.value = true
  editingId.value = null
  actionFeedback.value = '서버 예약 확인 중…'
  try {
    const schedule = await englishScraperApi.schedule()
    cloudSchedule.value = schedule
    draft.value = {
      enableSchedule: schedule.enabled,
      scheduledTime: englishScheduleTime(schedule),
      timezone: schedule.timezone,
      weekdays: [...schedule.weekdays]
    }
    editingId.value = id
    actionFeedback.value = ''
  } catch (error) {
    actionFeedback.value = error instanceof Error ? error.message : '서버 예약을 불러오지 못했습니다.'
  } finally {
    scheduleBusy.value = false
  }
}

async function saveSchedule() {
  if (!draft.value || scheduleBusy.value) return
  scheduleBusy.value = true
  try {
    cloudSchedule.value = await endpointsStore.saveEnglishSchedule(draft.value)
    editingId.value = null
    actionFeedback.value = '수집 예약이 서버에 저장되었습니다.'
  } catch (error) {
    actionFeedback.value = error instanceof Error ? error.message : '서버 예약을 저장하지 못했습니다.'
  } finally {
    scheduleBusy.value = false
  }
}

async function handleFetchNow(endpointId: string) {
  if (endpointsStore.isFetching(endpointId)) return
  actionFeedback.value = '수집 요청 중...'
  const res = await endpointsStore.triggerFetch(endpointId, true)
  if (res.success) {
    actionFeedback.value = `✓ 수집 성공: ${res.message}`
  } else {
    actionFeedback.value = `⚠️ 수집 실패: ${res.message} (홈 Pending 뷰에 Fetch 버튼 카드가 등록되었습니다)`
  }
}

function handleSimulateFiveFailures(endpointId: string) {
  const failedMsg = endpointsStore.simulateFiveFailedAttempts(endpointId)
  if (failedMsg) {
    actionFeedback.value = `✓ 5회 재시도 실패 시뮬레이션 완료! 홈(Pending) 뷰에 'Fetch' 버튼이 포함된 카드가 생성되었습니다.`
  }
}

function handleDelete(endpointId: string) {
  if (confirm('이 API 엔드포인트를 삭제하시겠습니까?')) {
    endpointsStore.deleteEndpoint(endpointId)
  }
}
</script>

<template>
  <SettingsPage title="등록된 API 엔드포인트">
    <section class="registered-endpoints settings-card" aria-labelledby="registered-endpoints-heading">
      <div class="card-title-row">
        <h3 id="registered-endpoints-heading" class="card-title">엔드포인트 목록 ({{ endpointsStore.endpoints.length }})</h3>
        <div class="endpoint-list-actions">
          <RouterLink :to="{ name: 'api-schedules' }" class="item-action-btn btn-schedules">수집 일정 보기</RouterLink>
          <RouterLink to="/register-api" class="item-action-btn btn-fetch">+ API 등록</RouterLink>
        </div>
      </div>
      <p v-if="actionFeedback" role="status" class="notif-feedback-box">{{ actionFeedback }}</p>
      <p v-if="!endpointsStore.endpoints.length" class="empty-endpoints-box">등록된 API 엔드포인트가 없습니다.</p>
      <div v-else class="endpoint-items-list" role="list">
        <article
          v-for="ep in endpointsStore.endpoints"
          :key="ep.id"
          class="endpoint-item"
          role="listitem"
        >
          <div class="item-header">
            <div class="item-title-group">
              <span class="method-badge">{{ ep.method }}</span>
              <strong class="item-name">{{ ep.name }}</strong>
            </div>
            <span class="status-pill" :class="`status-${collectionStatus(ep)}`">
              <template v-if="endpointsStore.isFetching(ep.id)">수집 중</template>
              <template v-else-if="ep.schedule.lastStatus === 'failed'">수집 실패 ({{ ep.schedule.currentAttempts }}/{{ ep.schedule.maxRetries }})</template>
              <template v-else-if="ep.schedule.lastStatus === 'success'">수집 정상</template>
              <template v-else>스케줄 대기</template>
            </span>
          </div>

          <div class="item-url font-mono">{{ ep.url }}</div>

          <button v-if="isEnglishEndpoint(ep)" type="button" class="setting-sub-btn"
            :disabled="scheduleBusy" @click="editSchedule(ep.id)">서버 수집 예약 변경</button>
          <form v-if="editingId === ep.id && draft" class="schedule-editor" @submit.prevent="saveSchedule">
            <label><input v-model="draft.enableSchedule" type="checkbox" class="switch-input" :disabled="scheduleBusy" /> 자동 수집 스케줄 활성화</label>
            <EnglishScheduleFields v-if="draft.enableSchedule"
              v-model:time="draft.scheduledTime" v-model:timezone="draft.timezone"
              v-model:weekdays="draft.weekdays" :disabled="scheduleBusy" :schedule="cloudSchedule"
            />
            <button type="submit" class="setting-action-btn" :disabled="scheduleBusy">수집 예약 저장</button>
            <button type="button" class="setting-sub-btn" :disabled="scheduleBusy" @click="editingId = null">취소</button>
          </form>
          <div class="item-schedule-meta">
            <span class="meta-tag">
              ⏰ 스케줄: {{ scheduleLabel(ep) }}
            </span>
            <span v-if="!isEnglishEndpoint(ep)" class="meta-tag">
              🔄 재시도: 최대 {{ ep.schedule.maxRetries }}회 ({{ ep.schedule.retryIntervalHours }}시간 간격)
            </span>
            <span v-if="ep.schedule.lastRunAt" class="meta-tag">
              🕒 최근 시도: {{ new Date(ep.schedule.lastRunAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="item-actions-row">
            <button
              type="button"
              class="item-action-btn btn-fetch"
              aria-label="지금 즉시 데이터 가져오기"
              :disabled="endpointsStore.isFetching(ep.id)"
              @click="handleFetchNow(ep.id)"
            >
              Fetch 지금 실행
            </button>
            <button
              type="button"
              class="item-action-btn btn-simulate-fail"
              title="5회 시도 후 최종 실패 상황을 시뮬레이션하여 홈 화면에 'Fetch' 버튼 카드를 생성합니다."
              aria-label="5회 실패 및 홈 Fetch 카드 생성 테스트"
              @click="handleSimulateFiveFailures(ep.id)"
            >
              5회 실패 테스트
            </button>
            <button
              type="button"
              class="item-action-btn btn-delete"
              aria-label="엔드포인트 삭제"
              @click="handleDelete(ep.id)"
            >
              삭제
            </button>
          </div>
        </article>
      </div>
    </section>
  </SettingsPage>
</template>

<style scoped>
.registered-endpoints button.btn-fetch:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
