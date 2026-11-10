<script setup lang="ts">
import TimePicker from '@/components/TimePicker.vue'
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import DatePicker from '@/components/DatePicker.vue'
import { useEndpointsStore } from '@/stores/endpoints'
const route = useRoute()
const endpointsStore = useEndpointsStore()
const selectedEndpoint = ref('')
const fetching = ref(false)
let request = 0
async function fillFromApi() {
  const currentRequest = ++request
  if (!selectedEndpoint.value) { fetching.value = false; feedback.value = ''; return }
  fetching.value = true
  feedback.value = ''
  try {
    const result = await endpointsStore.triggerFetch(selectedEndpoint.value, true)
    if (currentRequest !== request) return
    if (result.success && result.shareMessage) {
      message.value = result.shareMessage.body
      feedback.value = 'API 데이터를 메시지에 입력했습니다. 내용을 확인하고 수정할 수 있습니다.'
    } else { feedback.value = result.message }
  } catch (error) {
    if (currentRequest === request) feedback.value = error instanceof Error ? error.message : 'API 데이터를 불러오지 못했습니다.'
  } finally { if (currentRequest === request) fetching.value = false }
}
onMounted(() => {
  endpointsStore.loadEndpoints()
  const id = typeof route.query.endpoint === 'string' ? route.query.endpoint : ''
  selectedEndpoint.value = endpointsStore.endpoints.some(endpoint => endpoint.id === id) ? id : endpointsStore.endpoints[0]?.id || ''
})
watch(selectedEndpoint, fillFromApi)
watch(() => route.query.endpoint, id => {
  if (typeof id === 'string' && endpointsStore.endpoints.some(endpoint => endpoint.id === id)) selectedEndpoint.value = id
})
const room = ref('')
const message = ref('')
function today() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const due = ref(today())
const time = ref('09:00')
const editingTime = ref(false)
const feedback = ref('')
function download() {
  if (editingTime.value || fetching.value) return
  const date = new Date(`${due.value}T${time.value}`)
  if (!room.value.trim() || !message.value.trim() || !Number.isFinite(date.getTime()) || date.getTime() <= Date.now()) {
    feedback.value = '정확한 방 이름, 메시지, 미래 예약 시간을 입력하세요.'
    return
  }
  const payload = { version: 1, jobs: [{ id: crypto.randomUUID(), room: room.value, message: message.value, due: date.toISOString() }] }
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'moatok-openchat.json'
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  feedback.value = '예약 파일을 만들었습니다. Mac 도우미로 가져와야 예약이 활성화됩니다. 같은 파일을 다시 가져와도 중복 등록되지 않습니다.'
  // Each export creates a new ID. Clear inputs to avoid accidental duplicate schedules.
  message.value = ''
  due.value = today()
}
</script>
<template>
  <section class="settings-card openchat-schedule" aria-labelledby="openchat-title">
    <h3 id="openchat-title" class="card-title">오픈채팅 예약 전송 · Mac 도우미</h3>
    <p class="setting-caption">Mac 도우미가 실행 중이고 Mac이 깨어 있고 잠금 해제되어야 합니다. 대상 오픈채팅방을 별도 창으로 열어 두세요. 예약은 이 기기에서 파일로 내보내며 서버에 저장되지 않습니다.</p>
    <p class="setting-caption">방 제목이 정확히 일치하는 창 하나와 빈 입력창 하나만 허용합니다. 결과가 불확실하면 재전송하지 않고 확인 대기합니다. 발송 여부는 카카오톡에서 직접 확인하세요.</p>
    <form class="openchat-form" @submit.prevent="download">
      <label>카카오톡 창의 정확한 방 제목<input v-model="room" required maxlength="200" autocomplete="off"></label>
      <label>메시지 데이터 API
        <select v-model="selectedEndpoint"><option value="">직접 작성</option><option v-for="endpoint in endpointsStore.endpoints" :key="endpoint.id" :value="endpoint.id">{{ endpoint.name }}</option></select>
      </label>
      <div class="openchat-api-actions"><RouterLink to="/register-api">API 등록 및 관리</RouterLink><button v-if="selectedEndpoint" type="button" class="setting-sub-btn" :disabled="fetching" @click="fillFromApi">{{ fetching ? '불러오는 중…' : 'API 데이터 새로고침' }}</button></div>
      <label>메시지<textarea v-model="message" required rows="4" :disabled="fetching" /></label>
      <DatePicker id="openchat-date" v-model="due" label="예약 날짜 (이 기기의 시간대)" />
      <TimePicker id="openchat-time" v-model="time" label="예약 시간 (이 기기의 시간대)" @editing="editingTime = $event" />
      <button class="setting-action-btn" type="submit" :disabled="editingTime || fetching">예약 파일 다운로드</button>
    </form>
    <p v-if="feedback" role="status" class="setting-caption">{{ feedback }}</p>
    <details>
      <summary>Mac 도우미 설치 및 발송 확인</summary>
      <p class="setting-caption">Python 3.9 이상이 필요합니다. 도우미와 예약 파일을 같은 폴더에 저장하고 터미널에서 아래 명령을 실행하세요. 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용에서 터미널 권한을 허용하세요.</p>
      <a href="/openchat-helper.py" download>Mac 도우미 다운로드</a>
      <pre>python3 openchat-helper.py import moatok-openchat.json
python3 openchat-helper.py list
python3 openchat-helper.py run --send</pre>
      <p class="setting-caption">예약 ID로 취소: cancel ID · 카카오톡에서 확인 후 기록: confirm ID. 예약 시간보다 5분 이상 늦으면 발송하지 않습니다. 도우미는 자동 시작되지 않습니다. UI 구조가 맞지 않으면 발송을 중단합니다.</p>
      <p class="setting-caption">재가져오기는 같은 ID의 중복 실행을 막습니다. 새로운 파일로 같은 내용을 예약하면 별도 예약입니다. 이미 시도한 예약은 자동 재시도하지 않습니다.</p>
    </details>
  </section>
</template>
