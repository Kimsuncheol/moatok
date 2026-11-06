import type { ShareMessage } from '@/types'
import { getApiBaseUrl } from './api'
import { initKakaoSdk, loadKakaoSdkScript } from './kakao'

let token = ''
let expiresAt = 0
let sending = false
let connecting = false
export function clearMyChatConnection() { token = ''; expiresAt = 0 }

export async function connectMyChat(): Promise<void> {
  if (connecting) throw new Error('이미 카카오 연결이 진행 중입니다.')
  connecting = true
  const base = (import.meta.env.VITE_KAKAO_API_BASE_URL || getApiBaseUrl()).replace(/\/+$/, '')
  const origin = new URL(base).origin
  const popup = window.open('about:blank', 'moatok-kakao-login', 'width=480,height=700')
  try {
    if (!popup) throw new Error('팝업을 허용한 후 다시 연결하세요.')
    const status = await fetch(base + '/api/v1/kakao/status')
    const data = status.ok && status.headers.get('content-type')?.includes('application/json') ? await status.json() : null
    if (!data?.configured) throw new Error('카카오 연결 서버가 아직 설정되지 않았습니다.')
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => { clearTimeout(timer); clearInterval(poll); window.removeEventListener('message', receive) }
      const receive = (event: MessageEvent) => {
        if (event.origin !== origin || event.source !== popup || event.data?.type !== 'moatok-kakao-login') return
        cleanup()
        if (typeof event.data.access_token !== 'string' || !(event.data.expires_in > 0)) return reject(new Error(event.data.error || '카카오 연결에 실패했습니다.'))
        token = event.data.access_token
        expiresAt = Date.now() + Number(event.data.expires_in) * 1000 - 30_000
        resolve()
      }
      const timer = setTimeout(() => { cleanup(); reject(new Error('카카오 연결 시간이 초과되었습니다.')) }, 180_000)
      const poll = setInterval(() => { if (popup.closed) { cleanup(); reject(new Error('카카오 연결 창이 닫혔습니다.')) } }, 1000)
      window.addEventListener('message', receive)
      popup.location.href = base + '/api/v1/kakao/login'
    })
  } finally { popup?.close(); connecting = false }
}

export function buildMyChatTemplate(message: ShareMessage) {
  const text = message.body?.trim()
  if (!text) throw new Error('보낼 메시지 내용이 없습니다.')
  // Local cards may not have a server-backed detail page. Use the registered home URL.
  const link = window.location.origin + '/'
  return {object_type: 'text', text: text.length > 200 ? text.slice(0, 199) + '…' : text,
    link: {web_url: link, mobile_web_url: link}, button_title: '모아톡 열기'}
}

export async function sendToMyChat(message: ShareMessage): Promise<void> {
  if (sending) throw new Error('메시지를 전송 중입니다.')
  const template = buildMyChatTemplate(message)
  if (!token || Date.now() >= expiresAt) { clearMyChatConnection(); throw new Error('먼저 카카오 계정을 연결해 주세요.') }
  sending = true
  try {
    if (!await loadKakaoSdkScript() || !initKakaoSdk() || !window.Kakao?.API || !window.Kakao.Auth) throw new Error('카카오 JavaScript 키 또는 SDK 설정이 필요합니다.')
    window.Kakao.Auth.setAccessToken(token, false)
    const result = await window.Kakao.API.request({url: '/v2/api/talk/memo/default/send', data: {template_object: template}})
    if (result.result_code !== 0) throw new Error('카카오에서 전송 성공을 확인하지 못했습니다.')
  } catch (error: any) {
    if (error?.code === -401 || error?.code === -402) { clearMyChatConnection(); throw new Error('카카오 연결 또는 메시지 동의를 다시 진행해 주세요.') }
    throw error
  } finally { sending = false }
}
