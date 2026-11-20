import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { initiateKakaoShare } from '@/services/kakao'
import { useAuthStore } from '@/stores/auth'
import type { ShareMessage } from '@/types'

export const useShareAttemptsStore = defineStore('shareAttempts', () => {
  const auth = useAuthStore()
  const started = reactive(new Set<string>())

  function attemptKey(id: string) {
    return 'moatok_share_started:' + JSON.stringify([auth.userUid, id])
  }

  function hasStarted(id: string) {
    const key = attemptKey(id)
    if (started.has(key)) return true
    try { return sessionStorage.getItem(key) === '1' } catch { return false }
  }

  async function startShare(message: ShareMessage) {
    const key = attemptKey(message.id)
    const result = await initiateKakaoShare(message)
    if (result.success) {
      started.add(key)
      // Mobile browsers may reload Moatok when returning from KakaoTalk.
      try { sessionStorage.setItem(key, '1') } catch { /* In-memory state is still available. */ }
    }
    return result
  }

  return { hasStarted, startShare }
})
