<script setup lang="ts">
import { ref } from 'vue'
const room = ref('')
const message = ref('')
const due = ref('')
const time = ref('09:00')
const editingTime = ref(false)
const draftHour = ref('09')
const draftMinute = ref('00')
function openTimeEditor() {
  [draftHour.value, draftMinute.value] = time.value.split(':')
  editingTime.value = !editingTime.value
}
function applyTime() {
  time.value = `${draftHour.value}:${draftMinute.value}`
  editingTime.value = false
}
const feedback = ref('')
function download() {
  if (editingTime.value) return
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
  due.value = ''
}
</script>
<template>
  <section class="settings-card openchat-schedule" aria-labelledby="openchat-title">
    <h3 id="openchat-title" class="card-title">오픈채팅 예약 전송 · Mac 도우미</h3>
    <p class="setting-caption">Mac 도우미가 실행 중이고 Mac이 깨어 있고 잠금 해제되어야 합니다. 대상 오픈채팅방을 별도 창으로 열어 두세요. 예약은 이 기기에서 파일로 내보내며 서버에 저장되지 않습니다.</p>
    <p class="setting-caption">방 제목이 정확히 일치하는 창 하나와 빈 입력창 하나만 허용합니다. 결과가 불확실하면 재전송하지 않고 확인 대기합니다. 발송 여부는 카카오톡에서 직접 확인하세요.</p>
    <form class="openchat-form" @submit.prevent="download">
      <label>카카오톡 창의 정확한 방 제목<input v-model="room" required maxlength="200" autocomplete="off"></label>
      <label>메시지<textarea v-model="message" required maxlength="4000" rows="4" /></label>
      <label>예약 날짜 (이 기기의 시간대)<input v-model="due" type="date" required></label>
      <div class="automation-time-group">
        <span id="openchat-time-label">예약 시간 (이 기기의 시간대)</span>
        <button type="button" class="automation-time-trigger" aria-labelledby="openchat-time-label openchat-time-value" :aria-expanded="editingTime" aria-controls="openchat-time-editor" @click="openTimeEditor">
          <span id="openchat-time-value">{{ time }}</span>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </button>
        <div v-if="editingTime" id="openchat-time-editor" class="automation-time-editor">
          <label>시 <select v-model="draftHour"><option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">{{ String(h - 1).padStart(2, '0') }}</option></select></label>
          <label>분 <select v-model="draftMinute"><option v-for="m in 60" :key="m" :value="String(m - 1).padStart(2, '0')">{{ String(m - 1).padStart(2, '0') }}</option></select></label>
          <div class="automation-time-actions"><button type="button" @click="editingTime = false">취소</button><button type="button" @click="applyTime">설정</button></div>
        </div>
      </div>
      <button class="setting-action-btn" type="submit" :disabled="editingTime">예약 파일 다운로드</button>
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
