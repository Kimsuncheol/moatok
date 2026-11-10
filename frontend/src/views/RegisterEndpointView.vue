<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  useEndpointsStore,
  DEFAULT_ENGLISH_SCRAPPER_URL
} from '@/stores/endpoints'
import ScheduleWidget from '@/components/ScheduleWidget.vue'

const router = useRouter()
const endpointsStore = useEndpointsStore()

function goHome() {
  router.push('/')
}

const form = ref({
  name: '',
  url: '',
  method: 'POST' as 'GET' | 'POST',
  sourceType: 'english_scrapper' as 'english_scrapper' | 'generic_api',
  headersText: '',
  enableSchedule: true,
  scheduledTime: '09:00',
  maxRetries: 5,
  retryIntervalHours: 1
})

const formError = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const actionFeedback = ref<string | null>(null)

function fillChosunDailyTestUrl() {
  form.value.name = 'Chosun Daily Articles'
  form.value.url = 'https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10'
  form.value.method = 'GET'
  form.value.sourceType = 'generic_api'
  form.value.headersText = ''
  form.value.enableSchedule = false
  formError.value = null
  successMessage.value = '✓ 최신 조선일보 영어 기사 10개 테스트 엔드포인트 정보가 입력되었습니다.'
}

function fillJapaneseScrapperTestUrl() {
  form.value.name = 'Japanese Lessons API'
  form.value.url = 'https://japanese-scraper.onrender.com/api/articles?status=ready&page=1'
  form.value.method = 'GET'
  form.value.sourceType = 'generic_api'
  form.value.headersText = ''
  form.value.enableSchedule = false
  formError.value = null
  successMessage.value = '✓ 최신 일본어 수업 목록 테스트 엔드포인트 정보가 입력되었습니다.'
}

// Fill form with english_scrapper url for testing
function fillEnglishScrapperTestUrl() {
  form.value.name = 'English Scraper API'
  form.value.url = DEFAULT_ENGLISH_SCRAPPER_URL.replace(/\/+$/, '') + '/api/v1/lessons/fetch'
  form.value.method = 'POST'
  form.value.sourceType = 'english_scrapper'
  form.value.enableSchedule = true
  form.value.scheduledTime = '09:00'
  form.value.maxRetries = 5
  form.value.retryIntervalHours = 1
  formError.value = null
  successMessage.value = '✓ english_scrapper 테스트 엔드포인트 정보가 입력되었습니다.'
  setTimeout(() => {
    if (successMessage.value?.includes('테스트 엔드포인트')) {
      successMessage.value = null
    }
  }, 3000)
}

async function handleTestConnection() {
  formError.value = null
  if (!form.value.url.trim()) {
    formError.value = '테스트할 API 엔드포인트 URL을 입력하세요.'
    return
  }

  let headers: Record<string, string> | undefined
  if (form.value.headersText.trim()) {
    try {
      headers = JSON.parse(form.value.headersText.trim())
    } catch {
      formError.value = '헤더는 올바른 JSON 형식이어야 합니다 (예: {"Authorization": "Bearer ..."})'
      return
    }
  }

  await endpointsStore.testEndpoint({
    url: form.value.url,
    method: form.value.method,
    headers,
    sourceType: form.value.sourceType
  })
}

function handleRegister() {
  formError.value = null
  successMessage.value = null

  if (!form.value.url.trim()) {
    formError.value = 'API 엔드포인트 URL은 필수 항목입니다.'
    return
  }

  let headers: Record<string, string> | undefined
  if (form.value.headersText.trim()) {
    try {
      headers = JSON.parse(form.value.headersText.trim())
    } catch {
      formError.value = '헤더는 올바른 JSON 형식이어야 합니다.'
      return
    }
  }

  try {
    const isEnglish =
      form.value.sourceType === 'english_scrapper' ||
      form.value.url.includes('english-scrapper') ||
      form.value.url.includes('english_scrapper')

    const newEndpoint = endpointsStore.addEndpoint({
      name: form.value.name.trim() || (isEnglish ? 'English Scraper API' : 'API Endpoint'),
      url: form.value.url.trim(),
      method: form.value.method,
      headers,
      sourceType: isEnglish ? 'english_scrapper' : 'generic_api',
      schedule: {
        enabled: form.value.enableSchedule,
        scheduledTime: form.value.scheduledTime || '09:00',
        retryIntervalHours: 1, // 1 hour after scheduled time
        maxRetries: 5 // up to 5 times
      }
    })

    successMessage.value = `✓ 엔드포인트 '${newEndpoint.name}'이(가) 등록되었습니다.`
    form.value.name = ''
    form.value.url = ''
    form.value.headersText = ''

    setTimeout(() => {
      successMessage.value = null
    }, 4000)
  } catch (err: any) {
    formError.value = err.message || '엔드포인트 등록에 실패했습니다.'
  }
}

async function handleFetchNow(endpointId: string) {
  actionFeedback.value = '수집 요청 중...'
  const res = await endpointsStore.triggerFetch(endpointId, true)
  if (res.success) {
    actionFeedback.value = `✓ 수집 성공: ${res.message}`
  } else {
    actionFeedback.value = `⚠️ 수집 실패: ${res.message} (홈 Pending 뷰에 Fetch 버튼 카드가 등록되었습니다)`
  }
  setTimeout(() => {
    actionFeedback.value = null
  }, 4500)
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

onMounted(() => {
  endpointsStore.loadEndpoints()
  if (!endpointsStore.endpoints.length) {
    fillEnglishScrapperTestUrl()
  }
})
</script>

<template>
  <div class="register-endpoint-view">
    <!-- Navigation Back to Home -->
    <nav class="view-nav-bar" aria-label="이전 화면으로 이동">
      <button type="button" class="back-link" aria-label="홈 화면으로 돌아가기" @click="goHome">
        <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        <span>홈 (Pending)</span>
      </button>
      <span class="nav-current-title">API 엔드포인트 등록</span>
    </nav>

    <!-- Header Section -->
    <header class="view-header">
      <h1 class="view-title">Register an API endpoint</h1>
      <p class="view-desc">
        콘텐츠 수집을 위한 API 엔드포인트와 자동 수집(auto-fetching) 스케줄을 설정합니다.
      </p>
    </header>


    <div class="test-preset-box">
      <div class="preset-info">
        <strong class="preset-title">🧪 Chosun Daily endpoint for testing</strong>
        <span class="preset-sub">GET /api/v1/articles?page=1&amp;per_page=10 · 최신 영어 기사 10개</span>
      </div>
      <button type="button" class="preset-fill-btn" @click="fillChosunDailyTestUrl">
        조선일보 테스트 엔드포인트 채우기
      </button>
    </div>

    <!-- Quick fill test button for testing -->
    <div class="test-preset-box">
      <div class="preset-info">
        <strong class="preset-title">🧪 API endpoint for testing</strong>
        <span class="preset-sub">POST /api/v1/lessons/fetch · 최신 영어 수업 가져오기</span>
      </div>
      <button
        type="button"
        class="preset-fill-btn"
        aria-label="english_scrapper url 테스트 엔드포인트 자동 입력"
        @click="fillEnglishScrapperTestUrl"
      >
        테스트 엔드포인트 채우기
      </button>
    </div>

    <div class="test-preset-box">
      <div class="preset-info">
        <strong class="preset-title">🧪 Japanese lesson endpoint for testing</strong>
        <span class="preset-sub">GET /api/articles?status=ready&amp;page=1 · 최신 일본어 수업 목록</span>
      </div>
      <button
        type="button"
        class="preset-fill-btn"
        aria-label="japanese_scrapper 최신 수업 목록 테스트 엔드포인트 자동 입력"
        @click="fillJapaneseScrapperTestUrl"
      >
        일본어 테스트 엔드포인트 채우기
      </button>
    </div>

    <!-- Registration Form Card -->
    <section class="card form-card" aria-labelledby="endpoint-form-heading">
      <div class="card-header">
        <h2 id="endpoint-form-heading" class="card-title">엔드포인트 설정 (Endpoint Details)</h2>
        <span class="card-badge">REST API</span>
      </div>

      <form class="endpoint-form" @submit.prevent="handleRegister">
        <!-- Input: API Endpoint URL -->
        <div class="form-group">
          <label for="endpoint-url" class="form-label">
            API 엔드포인트 URL <span class="required-star">*</span>
          </label>
          <input
            id="endpoint-url"
            v-model="form.url"
            type="url"
            required
            placeholder="https://english-scrapper.onrender.com"
            class="form-input font-mono"
            maxlength="2048"
          />
          <span class="field-hint">데이터를 가져올 공개 HTTPS REST API 엔드포인트 주소를 입력합니다.</span>
        </div>

        <!-- Input: Endpoint Name -->
        <div class="form-group">
          <label for="endpoint-name" class="form-label">엔드포인트 명칭 (Name)</label>
          <input
            id="endpoint-name"
            v-model="form.name"
            type="text"
            placeholder="예: 오늘의 영어 스크래퍼"
            class="form-input"
            maxlength="100"
          />
        </div>

        <!-- HTTP Method & Source Type -->
        <div class="form-row-2">
          <div class="form-group">
            <label class="form-label">HTTP Method</label>
            <div class="method-selector" role="radiogroup" aria-label="HTTP Method 선택">
              <button
                type="button"
                class="method-toggle-btn"
                :class="{ active: form.method === 'POST' }"
                @click="form.method = 'POST'"
              >
                POST
              </button>
              <button
                type="button"
                class="method-toggle-btn"
                :class="{ active: form.method === 'GET' }"
                @click="form.method = 'GET'"
              >
                GET
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="source-type" class="form-label">엔드포인트 유형</label>
            <select
              id="source-type"
              v-model="form.sourceType"
              class="form-select"
            >
              <option value="english_scrapper">오늘의 영어 (english_scrapper)</option>
              <option value="generic_api">일반 JSON API</option>
            </select>
          </div>
        </div>

        <!-- Optional Headers -->
        <div class="form-group">
          <label for="endpoint-headers" class="form-label">
            HTTP 헤더 (Headers, 선택사항)
          </label>
          <textarea
            id="endpoint-headers"
            v-model="form.headersText"
            rows="2"
            placeholder='{"Authorization": "Bearer token"}'
            class="form-textarea font-mono"
          ></textarea>
        </div>

        <!-- Schedule Section -->
        <div class="schedule-config-section">
          <div class="schedule-section-header">
            <div class="schedule-header-text">
              <h3 class="schedule-title">스케줄 및 자동 수집 (Schedule)</h3>
              <p class="schedule-desc">API에서 데이터를 자동으로 수집(auto-fetching)하는 주기 및 재시도 규칙입니다.</p>
            </div>
            <label class="switch-container">
              <input
                type="checkbox"
                v-model="form.enableSchedule"
                class="switch-input"
                aria-label="자동 수집 스케줄 활성화"
              />
              <span class="switch-slider"></span>
            </label>
          </div>

          <div v-if="form.enableSchedule" class="schedule-body">
            <!-- Retry Rule Explanation Box -->
            <div class="retry-policy-box" role="note">
              <div class="policy-header">
                <span class="policy-badge">재시도 정책</span>
                <strong class="policy-title">최대 5회 시도 (1시간 간격 재시도)</strong>
              </div>
              <ul class="policy-list">
                <li>
                  <strong>1차 시도:</strong> 설정한 예정 시각(<code>{{ form.scheduledTime }}</code>)에 자동 수집을 1차 시도합니다.
                </li>
                <li>
                  <strong>재시도 규칙:</strong> 수집 실패 시, <strong>예정 시각 1시간 후마다 1회씩 최대 5회</strong>까지 순차적으로 재시도합니다.
                </li>
                <li>
                  <strong>최종 실패 시 홈 뷰 연동:</strong> 5회 시도 후에도 데이터 수집에 실패하면, <strong>홈(Pending) 뷰의 카드에 'Fetch' 버튼</strong>이 제공되어 사용자가 수동으로 언제든지 다시 가져올 수 있습니다 (기존 retry 버튼 대체).
                </li>
              </ul>
            </div>

            <!-- Schedule-X Calendar Widget -->
            <ScheduleWidget
              v-model:scheduled-time="form.scheduledTime"
              :endpoint-name="form.name || 'API Endpoint'"
              :enabled="form.enableSchedule"
            />
          </div>
        </div>

        <!-- Test Connection Result Feedback -->
        <div
          v-if="endpointsStore.testResult"
          class="test-result-box"
          :class="endpointsStore.testResult.success ? 'test-success' : 'test-failure'"
          role="status"
          aria-live="polite"
        >
          <div class="result-icon">{{ endpointsStore.testResult.success ? '✓' : '⚠️' }}</div>
          <div class="result-text">
            <strong>{{ endpointsStore.testResult.success ? '연결 테스트 성공' : '연결 테스트 확인 필요' }}</strong>
            <p>{{ endpointsStore.testResult.message }}</p>
          </div>
        </div>

        <!-- Form Error / Success Alerts -->
        <div v-if="formError" class="form-alert error-alert" role="alert">
          {{ formError }}
        </div>
        <div v-if="successMessage" class="form-alert success-alert" role="status">
          {{ successMessage }}
        </div>

        <!-- Form Buttons Row -->
        <div class="form-actions-row">
          <button
            type="button"
            class="btn-test"
            :disabled="endpointsStore.testing || !form.url.trim()"
            @click="handleTestConnection"
          >
            {{ endpointsStore.testing ? '연결 테스트 중...' : '연결 테스트' }}
          </button>
          <button
            type="submit"
            class="btn-submit"
            :disabled="endpointsStore.testing || !form.url.trim()"
          >
            엔드포인트 등록
          </button>
        </div>
      </form>
    </section>

    <!-- Action feedback notification -->
    <div v-if="actionFeedback" class="action-feedback-toast" role="status">
      {{ actionFeedback }}
    </div>

    <!-- Registered Endpoints List -->
    <section class="card list-card" aria-labelledby="registered-endpoints-heading">
      <div class="card-header">
        <h2 id="registered-endpoints-heading" class="card-title">등록된 API 엔드포인트 목록</h2>
        <span class="count-badge">{{ endpointsStore.endpoints.length }}개</span>
      </div>

      <div v-if="endpointsStore.endpoints.length === 0" class="empty-endpoints-box">
        <p>등록된 API 엔드포인트가 없습니다. 위 폼에서 새로 등록해주세요.</p>
      </div>

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
            <span
              class="status-pill"
              :class="{
                'status-success': ep.schedule.lastStatus === 'success',
                'status-failed': ep.schedule.lastStatus === 'failed',
                'status-idle': ep.schedule.lastStatus === 'idle',
                'status-fetching': ep.schedule.lastStatus === 'fetching'
              }"
            >
              {{
                ep.schedule.lastStatus === 'success'
                  ? '수집 정상'
                  : ep.schedule.lastStatus === 'failed'
                  ? `5회 실패 (${ep.schedule.currentAttempts}/5)`
                  : ep.schedule.lastStatus === 'fetching'
                  ? '수집 중'
                  : '스케줄 대기'
              }}
            </span>
          </div>

          <div class="item-url font-mono">{{ ep.url }}</div>

          <div class="item-schedule-meta">
            <span class="meta-tag">
              ⏰ 스케줄: {{ ep.schedule.enabled ? `매일 ${ep.schedule.scheduledTime}` : '비활성' }}
            </span>
            <span class="meta-tag">
              🔄 재시도: 최대 {{ ep.schedule.maxRetries }}회 (1시간 간격)
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

    <!-- Bottom link to return home -->
    <div class="bottom-home-link-box">
      <button type="button" class="bottom-home-btn" @click="goHome">
        홈 (Pending 대기 목록)으로 이동
      </button>
    </div>
  </div>
</template>

<style scoped>
.register-endpoint-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  max-width: 480px;
  margin: 0 auto;
  padding-bottom: 80px;
}

/* Nav Bar */
.view-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 4px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  transition: all 0.15s ease;
}

.back-link:hover {
  border-color: var(--border-strong);
  background-color: var(--bg-surface-hover);
}

.back-icon {
  width: 14px;
  height: 14px;
}

.nav-current-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

/* View Header */
.view-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.view-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.view-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.45;
}

/* Test Preset Box */
.test-preset-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background-color: var(--bg-surface-elevated);
  border: 1px dashed var(--border-strong);
  gap: 12px;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.preset-title {
  font-size: 13px;
  color: var(--text-primary);
}

.preset-sub {
  font-size: 11.5px;
  color: var(--text-muted);
}

.preset-fill-btn {
  padding: 6px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.preset-fill-btn:hover {
  border-color: var(--border-strong);
  background-color: var(--bg-surface-hover);
}

/* Cards */
.card {
  padding: 16px;
  border-radius: 12px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-badge,
.count-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

/* Form Styles */
.endpoint-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.required-star {
  color: var(--accent-action);
}

.field-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-size: 13px;
  box-sizing: border-box;
  transition: border-color 0.15s ease;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--border-strong);
}

.form-textarea {
  resize: vertical;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 10px;
}

.method-selector {
  display: flex;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  overflow: hidden;
  height: 40px;
}

.method-toggle-btn {
  flex: 1;
  background: var(--bg-surface-elevated);
  border: none;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.method-toggle-btn.active {
  background: var(--accent-action);
  color: var(--accent-action-text);
}

/* Schedule Section */
.schedule-config-section {
  padding: 14px;
  border-radius: 10px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.schedule-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.schedule-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.schedule-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.schedule-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.schedule-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.schedule-time-input {
  max-width: 160px;
}

/* Toggle Switch */
.switch-container {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch-input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--border-default);
  transition: 0.2s;
  border-radius: 24px;
}

.switch-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: var(--bg-surface);
  transition: 0.2s;
  border-radius: 50%;
}

.switch-input:checked + .switch-slider {
  background-color: var(--accent-action);
}

.switch-input:checked + .switch-slider:before {
  transform: translateX(20px);
  background-color: var(--accent-action-text);
}

/* Retry Policy Box */
.retry-policy-box {
  padding: 12px;
  border-radius: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-subtle, var(--border-default));
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.policy-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.policy-badge {
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 4px;
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.policy-title {
  font-size: 12.5px;
  color: var(--text-primary);
}

.policy-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.policy-list code {
  font-family: var(--font-mono);
  background-color: var(--bg-surface-elevated);
  padding: 1px 4px;
  border-radius: 3px;
}

/* Test Result Box */
.test-result-box {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background-color: var(--bg-surface-elevated);
}

.test-success {
  border-color: var(--border-strong);
}

.result-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.result-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: var(--text-primary);
}

.result-text p {
  margin: 0;
  color: var(--text-secondary);
}

/* Form Alerts */
.form-alert {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
}

.error-alert {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
}

.success-alert {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--accent-action);
  color: var(--text-primary);
}

/* Form Actions */
.form-actions-row {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 10px;
  margin-top: 6px;
}

.btn-test {
  padding: 10px 14px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  min-height: 44px;
  transition: all 0.15s ease;
}

.btn-test:hover:not(:disabled) {
  border-color: var(--border-strong);
  background-color: var(--bg-surface-hover);
}

.btn-submit {
  padding: 10px 14px;
  border-radius: 8px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  min-height: 44px;
  transition: opacity 0.15s ease;
}

.btn-submit:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-test:disabled,
.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Toast */
.action-feedback-toast {
  padding: 12px 14px;
  border-radius: 8px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-strong);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Endpoints List */
.empty-endpoints-box {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.endpoint-items-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.endpoint-item {
  padding: 14px;
  border-radius: 10px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.item-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.method-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 800;
  padding: 2px 5px;
  border-radius: 4px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.item-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.status-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid var(--border-default);
}

.status-success {
  background-color: var(--badge-bg);
  color: var(--text-primary);
}

.status-failed {
  background-color: var(--badge-bg);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.status-idle,
.status-fetching {
  background-color: var(--bg-surface);
  color: var(--text-secondary);
}

.item-url {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.item-schedule-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.meta-tag {
  font-size: 11.5px;
  color: var(--text-secondary);
  background-color: var(--bg-surface);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle, var(--border-default));
}

.item-actions-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.item-action-btn {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  min-height: 34px;
  transition: all 0.15s ease;
}

.btn-fetch {
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border: none;
}

.btn-fetch:hover {
  opacity: 0.9;
}

.btn-simulate-fail {
  background-color: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-simulate-fail:hover {
  border-color: var(--border-strong);
}

.btn-delete {
  background-color: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-default);
  margin-left: auto;
}

.btn-delete:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

/* Bottom home link */
.bottom-home-link-box {
  margin-top: 8px;
  text-align: center;
}

.bottom-home-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 44px;
  padding: 12px 16px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.bottom-home-btn:hover {
  background-color: var(--bg-surface-hover);
  border-color: var(--border-strong);
}
/* The registration page is a narrow mobile surface, including on desktop. */
.test-preset-box {
  flex-direction: column;
  align-items: stretch;
}
.preset-info { min-width: 0; }
.preset-title, .preset-sub { overflow-wrap: anywhere; }
.preset-fill-btn {
  width: 100%;
  min-height: 44px;
  white-space: normal;
  line-height: 1.5;
}
.register-endpoint-view { width: 100%; box-sizing: border-box; }
.register-endpoint-view > * { min-width: 0; }
.view-nav-bar { gap: 12px; flex-wrap: wrap; }
.form-row-2 { grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); }
.form-row-2 > * { min-width: 0; }
.form-input, .form-select, .form-textarea { min-width: 0; box-sizing: border-box; }
@media (max-width: 380px) {
  .form-row-2, .form-actions-row { grid-template-columns: minmax(0, 1fr); }
}
</style>
