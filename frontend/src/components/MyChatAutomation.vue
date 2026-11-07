<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { myChatAutomationApi, type MyChatAutomation } from '@/services/api'
const settings = ref<MyChatAutomation>({ connected: false, on_new: false, daily: false, daily_time: '09:00', error: '' })
const busy = ref(false)
const configured = ref(false)
const loading = ref(true)
const unavailable = '자동 전송 서버 설정이 완료되지 않았습니다. 관리자에게 카카오 연결 설정을 요청해 주세요.'
const feedback = ref('')
async function load() {
  try { settings.value = await myChatAutomationApi.get() }
  catch (error) { feedback.value = error instanceof Error ? error.message : '설정을 불러오지 못했습니다.'; throw error }
}
onMounted(async () => {
  try {
    configured.value = (await myChatAutomationApi.status()).configured
    if (!configured.value) { feedback.value = unavailable; return }
    await load()
  } catch (error) { feedback.value = error instanceof Error ? error.message : '서버 상태를 확인하지 못했습니다.' }
  finally { loading.value = false }
})
async function save() {
  if (busy.value || !configured.value || !settings.value.connected) return
  busy.value = true
  try { settings.value = await myChatAutomationApi.save(settings.value); feedback.value = '자동 전송 설정을 저장했습니다.' }
  catch (error) { feedback.value = error instanceof Error ? error.message : '저장 실패' }
  finally { busy.value = false }
}
async function connect() {
  if (busy.value || loading.value || !configured.value) return
  const popup = window.open('about:blank', 'moatok-automation', 'width=480,height=700')
  if (!popup) { feedback.value = '팝업을 허용해 주세요.'; return }
  busy.value = true
  try {
    const { url } = await myChatAutomationApi.connect()
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => { window.removeEventListener('message', receive); clearTimeout(timer); clearInterval(poll) }
      const receive = (event: MessageEvent) => {
        if (event.source !== popup || event.origin !== new URL(url).origin || event.data?.type !== 'moatok-kakao-login') return
        cleanup()
        if (event.data.automation_connected) resolve()
        else reject(new Error(event.data.error || '연결 실패'))
      }
      const timer = setTimeout(() => { cleanup(); reject(new Error('연결 시간이 초과되었습니다.')) }, 180000)
      const poll = setInterval(() => { if (popup.closed) { cleanup(); reject(new Error('연결 창이 닫혔습니다.')) } }, 1000)
      window.addEventListener('message', receive)
      popup.location.href = url
    })
    await load()
    feedback.value = '연결되었습니다. 원하는 자동 전송을 선택하고 저장하세요.'
  } catch (error) { feedback.value = error instanceof Error ? error.message : '연결 실패' }
  finally { popup.close(); busy.value = false }
}
async function disconnect() {
  if (busy.value) return
  busy.value = true
  try { settings.value = await myChatAutomationApi.disconnect(); feedback.value = '자동 전송 연결을 해제했습니다.' }
  catch (error) { feedback.value = error instanceof Error ? error.message : '해제 실패' }
  finally { busy.value = false }
}
</script>
<template>
  <section class="settings-card my-chat-automation" aria-labelledby="automation-title">
    <h3 id="automation-title" class="card-title">나와의 채팅 자동 전송</h3>
    <p class="setting-caption">앱이 닫혀 있어도 서버에 새로 수집된 콘텐츠와 매일 모음을 나와의 채팅으로 보냅니다. 브라우저에만 저장한 콘텐츠는 제외됩니다.</p>
    <p class="setting-caption">새 콘텐츠는 수집 후 약 5분 이내, 매일 모음은 선택한 시간 이후 약 5분 이내에 전송합니다. 두 기능을 켜면 모음에 이미 보낸 내용이 포함될 수 있습니다. 메시지는 200자로 요약됩니다.</p>
    <button class="setting-action-btn" :disabled="busy || loading || !configured" @click="settings.connected ? disconnect() : connect()">{{ loading ? '서버 확인 중…' : busy ? '처리 중…' : settings.connected ? '자동 전송 연결 해제' : '자동 전송용 카카오 연결' }}</button>
    <fieldset class="automation-options" :disabled="busy || loading || !configured || !settings.connected">
      <legend>자동 전송 선택</legend>
      <label><input v-model="settings.on_new" type="checkbox"> 새 콘텐츠가 수집되면 전송</label>
      <label><input v-model="settings.daily" type="checkbox"> 매일 최신 콘텐츠 모음 전송</label>
      <label>매일 전송 시간 (한국 시간) <input v-model="settings.daily_time" type="time" required></label>
      <button class="setting-action-btn" @click="save">설정 저장</button>
    </fieldset>
    <p v-if="feedback || settings.error" class="automation-feedback" role="status">{{ feedback || settings.error }}</p>
  </section>
</template>
