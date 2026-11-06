<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ShareMessage } from '@/types'
import { myChatConnected, connectMyChat, disconnectMyChat, sendToMyChat, buildMyChatTemplate } from '@/services/kakaoMyChat'
const props = defineProps<{message: ShareMessage}>()
const expanded = ref(false)
const busy = ref(false)
const feedback = ref('')
const sent = ref(false)
const preview = computed(() => { try { return buildMyChatTemplate(props.message).text } catch { return '' } })
async function toggleConnection() {
  if (busy.value) return
  if (myChatConnected.value) return disconnect()
  busy.value = true
  try { await connectMyChat(); feedback.value = '연결되었습니다. 본문을 확인하고 전송을 눌러 주세요.' }
  catch (error) { feedback.value = error instanceof Error ? error.message : '연결에 실패했습니다.' }
  finally { busy.value = false }
}
async function disconnect() {
  busy.value = true
  try { await disconnectMyChat(); feedback.value = '이 브라우저의 카카오 연결을 해제했습니다.' }
  catch (error) { feedback.value = error instanceof Error ? error.message : '연결 해제에 실패했습니다.' }
  finally { busy.value = false }
}
async function send() {
  if (busy.value || sent.value) return
  busy.value = true
  try { await sendToMyChat(props.message); sent.value = true; feedback.value = '나와의 채팅에 전송했습니다.' }
  catch (error) { feedback.value = error instanceof Error ? error.message : '전송 결과를 확인하지 못했습니다. 카카오톡을 확인한 후 다시 시도하세요.' }
  finally { busy.value = false }
}
</script>
<template>
  <div class="my-chat-send" @click.stop @keydown.stop>
    <button type="button" @click="expanded = !expanded">나와의 채팅에 보내기</button>
    <div v-if="expanded">
      <p>받는 곳: 로그인한 카카오 계정의 나와의 채팅</p>
      <pre>{{ preview }}</pre>
      <p v-if="message.body.length > 200">카카오 텍스트 제한으로 본문은 200자 이내로 전송됩니다.</p>
      <p role="status">{{ myChatConnected ? '연결됨' : '연결 안 됨' }}</p>
      <button type="button" :disabled="busy" @click="toggleConnection">{{ busy ? '처리 중…' : myChatConnected ? '카카오 연결 해제' : '카카오 계정 연결' }}</button>
      <p>로그인 상태는 이 브라우저에 유지됩니다. 다시 열면 연결을 자동 복원합니다. 팝업 허용이 필요합니다.</p>
      <button type="button" :disabled="busy || sent || !preview" @click="send">{{ sent ? '전송 완료' : busy ? '처리 중…' : '확인 후 전송' }}</button>
      <p role="status">{{ feedback }}</p>
    </div>
  </div>
</template>
<style scoped>
.my-chat-send { margin-top: 0.75rem; }
.my-chat-send button { padding: 0.65rem; margin: 0.25rem; border: 1px solid currentColor; border-radius: 8px; background: transparent; color: inherit; cursor: pointer; }
.my-chat-send pre { white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }
.my-chat-send button:disabled { opacity: .5; cursor: default; }
</style>
