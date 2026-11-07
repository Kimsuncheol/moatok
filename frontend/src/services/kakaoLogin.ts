import { getApiBaseUrl } from './api'

export async function loginWithKakao(): Promise<string> {
  const url = new URL('/api/v1/kakao/signin', getApiBaseUrl() || window.location.origin)
  const popup = window.open(url.href, 'moatok-kakao-signin', 'width=480,height=700')
  if (!popup) throw new Error('팝업을 허용한 후 다시 로그인해 주세요.')
  try {
    return await new Promise<string>((resolve, reject) => {
      const cleanup = () => { clearTimeout(timer); clearInterval(poll); window.removeEventListener('message', receive) }
      const receive = (event: MessageEvent) => {
        if (event.source !== popup || event.origin !== url.origin || event.data?.type !== 'moatok-kakao-login') return
        cleanup()
        if (typeof event.data.firebase_token === 'string' && event.data.firebase_token) resolve(event.data.firebase_token)
        else reject(new Error(event.data.error || '카카오 로그인에 실패했습니다.'))
      }
      const timer = setTimeout(() => { cleanup(); reject(new Error('로그인 시간이 초과되었습니다. 다시 시도해 주세요.')) }, 180000)
      const poll = setInterval(() => { if (popup.closed) { cleanup(); reject(new Error('로그인 창이 닫혔습니다.')) } }, 1000)
      window.addEventListener('message', receive)
    })
  } finally { popup.close() }
}
