import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useAuthStore } from './auth'
import { myChatAutomationApi, type MyChatAutomation } from '@/services/api'

export const useSharingScheduleStore = defineStore('sharingSchedule', () => {
  const auth = useAuthStore()
  const settings = ref<MyChatAutomation | null>(null)
  const loading = ref(false)
  const unavailable = ref(false)
  let generation = 0
  let checkedAt = 0
  async function refresh(force = false) {
    if (!auth.isAuthenticated || loading.value || (!force && Date.now() - checkedAt < 60_000)) return
    const current = generation
    loading.value = true
    unavailable.value = false
    try {
      const result = await myChatAutomationApi.get()
      if (current === generation) { settings.value = result; checkedAt = Date.now() }
    } catch {
      if (current === generation) { unavailable.value = true; settings.value = null; checkedAt = Date.now() }
    } finally { if (current === generation) loading.value = false }
  }
  watch(() => [auth.userUid, auth.isAuthenticated], () => {
    generation++
    settings.value = null
    loading.value = false
    unavailable.value = false
    checkedAt = 0
    void refresh()
  }, { immediate: true })
  return { settings, loading, unavailable, refresh }
})
