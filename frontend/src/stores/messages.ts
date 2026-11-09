import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ShareMessage } from '@/types'
import { api } from '@/services/api'

const SAMPLE_INITIAL_MESSAGES: ShareMessage[] = [
  {
    id: 'smsg_sample_1',
    article_id: 'art_sample_1',
    source_name: 'Tech Briefing',
    title: '구글 클라우드 런 배포 및 보안 권한 가이드',
    body: `[모아톡 브리핑] 구글 클라우드 런 배포 및 보안 권한 가이드\n\n최소 권한 원칙(Least Privilege)에 따른 전용 서비스 계정 분리와 OIDC 기반 Cloud Scheduler 인증 체계를 안내합니다.\n\n🔗 https://feeds.example.com/articles/cloud-run-iam`,
    target_url: 'https://feeds.example.com/articles/cloud-run-iam',
    status: 'pending',
    kakao_shared: false,
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    notification_attempts: 1,
    last_notification_status: 'sent',
    items: [
      {
        title: '구글 클라우드 런 배포 및 보안 권한 가이드',
        url: 'https://feeds.example.com/articles/cloud-run-iam',
        source_name: 'Tech Briefing',
        summary: '최소 권한 원칙(Least Privilege)에 따른 전용 서비스 계정 분리와 OIDC 기반 Cloud Scheduler 인증 체계를 안내합니다.'
      }
    ],
    kakao_share_payload: {
      template_type: 'text',
      title: '구글 클라우드 런 배포 및 보안 권한 가이드',
      description: '최소 권한 원칙에 따른 전용 서비스 계정과 OIDC 스케줄러 인증 가이드',
      text: `[모아톡 브리핑] 구글 클라우드 런 배포 및 보안 권한 가이드\n\n최소 권한 원칙(Least Privilege)에 따른 전용 서비스 계정 분리와 OIDC 기반 Cloud Scheduler 인증 체계를 안내합니다.\n\n🔗 https://feeds.example.com/articles/cloud-run-iam`,
      primary_web_url: 'https://feeds.example.com/articles/cloud-run-iam',
      button_title: '원문 확인하기',
      requires_user_action_in_flutter: true
    }
  },
  {
    id: 'smsg_sample_2',
    article_id: 'art_sample_2',
    source_name: 'Frontend Hub',
    title: '모바일 우선 Vue 3 PWA 카카오톡 공유 아키텍처',
    body: `[모아톡 브리핑] 모바일 우선 Vue 3 PWA 카카오톡 공유 아키텍처\n\n백엔드 자동 게시가 아닌 사용자 주도형 카카오톡 공유 워크플로우를 제공합니다.\n\n🔗 https://feeds.example.com/articles/vue3-pwa-kakao`,
    target_url: 'https://feeds.example.com/articles/vue3-pwa-kakao',
    status: 'pending',
    kakao_shared: false,
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    notification_attempts: 1,
    last_notification_status: 'sent',
    items: [
      {
        title: '모바일 우선 Vue 3 PWA 카카오톡 공유 아키텍처',
        url: 'https://feeds.example.com/articles/vue3-pwa-kakao',
        source_name: 'Frontend Hub',
        summary: '백엔드 자동 게시가 아닌 사용자 주도형 카카오톡 공유 워크플로우를 제공합니다.'
      }
    ]
  }
]

export const LOCAL_MESSAGES_KEY = 'moatok_local_fetched_messages_v1'
function readLocalMessages(): ShareMessage[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(LOCAL_MESSAGES_KEY) || '[]')
    return Array.isArray(parsed) ? parsed.filter(m => m && typeof m.id === 'string' &&
      typeof m.title === 'string' && typeof m.body === 'string' && typeof m.endpoint_id === 'string') : []
  } catch { return [] }
}
function isShared(message: ShareMessage) {
  return message.kakao_shared || ['shared', 'shared_by_user'].includes(message.status || '')
}
function uniqueMessages(messages: ShareMessage[]) {
  return [...new Map(messages.map(message => [message.id, message])).values()]
}

export const useMessagesStore = defineStore('messages', () => {
  const deletedKey = 'moatok_deleted_messages_v1'
  const deletedIds = ref<string[]>([])
  try { deletedIds.value = JSON.parse(localStorage.getItem(deletedKey) || '[]') } catch { /* Empty on unavailable storage. */ }
  function deleteMessage(id: string) {
    const next = [...new Set([...deletedIds.value, id])]
    localStorage.setItem(deletedKey, JSON.stringify(next))
    deletedIds.value = next
    persistLocal(localMessages.value.filter(m => m.id !== id))
    pendingMessages.value = pendingMessages.value.filter(m => m.id !== id)
    if (selectedMessage.value?.id === id) selectedMessage.value = null
  }
  const storageWarning = ref<string | null>(null)
  const localMessages = ref<ShareMessage[]>(readLocalMessages())
  const pendingMessages = ref<ShareMessage[]>(localMessages.value.length ? localMessages.value.filter(m => !isShared(m)) : [...SAMPLE_INITIAL_MESSAGES])
  pendingMessages.value = pendingMessages.value.filter(m => !deletedIds.value.includes(m.id))
  const historyMessages = ref<ShareMessage[]>(localMessages.value.filter(isShared))
  const selectedMessage = ref<ShareMessage | null>(null)
  const loading = ref<boolean>(false)
  const refreshing = ref<boolean>(false)
  const error = ref<string | null>(null)

  function mergePending(remote: ShareMessage[]) {
    const localIds = new Set(localMessages.value.map(m => m.id))
    return uniqueMessages([...localMessages.value.filter(m => !isShared(m)), ...remote.filter(m => !localIds.has(m.id))]).filter(m => !deletedIds.value.includes(m.id))
  }
  function mergeHistory(remote: ShareMessage[]) {
    return uniqueMessages([...localMessages.value.filter(isShared), ...remote])
  }
  function persistLocal(messages: ShareMessage[]) {
    // A failed storage write must not be reported as a durable successful fetch.
    try {
      window.localStorage.setItem(LOCAL_MESSAGES_KEY, JSON.stringify(messages))
      storageWarning.value = null
    } catch {
      storageWarning.value = '기기 저장소를 사용할 수 없어 이번 실행 중에만 브리핑이 유지됩니다.'
    }
    localMessages.value = messages
  }
  function upsertLocalMessage(message: ShareMessage) {
    if (message.fetch_status === 'success') {
      message.id = `local_${encodeURIComponent(message.target_url || message.id)}`
    }
    if (deletedIds.value.includes(message.id)) return message
    const existing = localMessages.value.find(m => m.id === message.id)
    if (existing && isShared(existing)) return existing
    const next = localMessages.value.filter(m => m.id !== message.id &&
      !(m.endpoint_id === message.endpoint_id && m.fetch_status === 'failed'))
    persistLocal([message, ...next])
    pendingMessages.value = mergePending(pendingMessages.value.filter(m => !m.id.startsWith('smsg_sample_') &&
      !(m.endpoint_id === message.endpoint_id && m.fetch_status === 'failed')))
    return message
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('storage', event => {
      if (event.key !== LOCAL_MESSAGES_KEY) return
      localMessages.value = readLocalMessages()
      pendingMessages.value = mergePending(pendingMessages.value.filter(m => !m.endpoint_id && !m.id.startsWith('smsg_sample_')))
      historyMessages.value = mergeHistory(historyMessages.value.filter(m => !m.endpoint_id))
    })
  }

  const pendingCount = computed(() => pendingMessages.value.length)
  const historyCount = computed(() => historyMessages.value.length)

  async function fetchPending(isRefresh = false) {
    if (isRefresh) {
      refreshing.value = true
    } else {
      loading.value = true
    }
    error.value = null

    try {
      const res = await api.getPendingMessages()
      if (res && Array.isArray(res.messages)) {
        pendingMessages.value = mergePending(res.messages)
      }
    } catch (err: any) {
      console.warn('API fetch pending messages failed:', err)
      error.value = err.message || '공유 대기 메시지를 불러오지 못했습니다.'
    } finally {
      loading.value = false
      refreshing.value = false
    }
  }

  async function fetchHistory(isRefresh = false): Promise<ShareMessage[]> {
    if (isRefresh) {
      refreshing.value = true
    } else {
      loading.value = true
    }
    error.value = null

    try {
      const allRes = await api.getAllMessages(100)
      if (allRes && Array.isArray(allRes.messages)) {
        // Reliable backend event filtering:
        // Include only items with share started (attempts > 0) or share confirmed (kakao_shared / shared status)
        historyMessages.value = allRes.messages.filter(
          (m) =>
            m.kakao_shared === true ||
            m.status === 'shared' ||
            m.status === 'shared_by_user' ||
            (m.share_attempt_count !== undefined && m.share_attempt_count > 0) ||
            !!m.last_share_attempt_at
        )
      } else {
        const historyRes = await api.getHistoryMessages()
        if (historyRes && Array.isArray(historyRes.messages)) {
          historyMessages.value = mergeHistory(historyRes.messages)
        }
      }
    } catch (err: any) {
      console.warn('API fetch history failed:', err)
      error.value = err.message || '공유 이력을 불러오지 못했습니다.'
    } finally {
      loading.value = false
      refreshing.value = false
    }
    historyMessages.value = mergeHistory(historyMessages.value)
    return historyMessages.value
  }

  async function fetchAll(isRefresh = false) {
    if (isRefresh) {
      refreshing.value = true
    } else {
      loading.value = true
    }
    error.value = null

    try {
      // 1. Fetch pending messages
      const pendingRes = await api.getPendingMessages()
      if (pendingRes && Array.isArray(pendingRes.messages)) {
        pendingMessages.value = mergePending(pendingRes.messages)
      }

      // 2. Fetch history messages supported by reliable backend events
      const allRes = await api.getAllMessages(100)
      if (allRes && Array.isArray(allRes.messages)) {
        historyMessages.value = allRes.messages.filter(
          (m) =>
            m.kakao_shared === true ||
            m.status === 'shared' ||
            m.status === 'shared_by_user' ||
            (m.share_attempt_count !== undefined && m.share_attempt_count > 0) ||
            !!m.last_share_attempt_at
        )
      } else {
        const historyRes = await api.getHistoryMessages()
        if (historyRes && Array.isArray(historyRes.messages)) {
          historyMessages.value = mergeHistory(historyRes.messages)
        }
      }
    } catch (err: any) {
      console.warn('API fetch failed, retaining existing messages:', err)
      error.value = err.message || '메시지 목록을 불러오지 못했습니다.'
    } finally {
      historyMessages.value = mergeHistory(historyMessages.value)
      loading.value = false
      refreshing.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  async function fetchById(messageId: string): Promise<ShareMessage | null> {
    if (deletedIds.value.includes(messageId)) return null
    const cached =
      pendingMessages.value.find((m) => m.id === messageId) ||
      historyMessages.value.find((m) => m.id === messageId)
    if (cached) {
      selectedMessage.value = cached
      return cached
    }

    try {
      const res = await api.getMessageById(messageId)
      if (res && res.message) {
        selectedMessage.value = res.message
        return res.message
      }
    } catch (err) {
      console.warn('Failed to fetch message by ID from API:', err)
    }

    return null
  }

  async function markAsShared(messageId: string, shareChannel = 'kakaotalk_web_pwa'): Promise<ShareMessage | null> {
    const nowIso = new Date().toISOString()
    let foundMsg: ShareMessage | null = null

    // Find and update in pendingMessages
    const pendingIdx = pendingMessages.value.findIndex((m) => m.id === messageId)
    if (pendingIdx !== -1) {
      foundMsg = {
        ...pendingMessages.value[pendingIdx],
        status: 'shared',
        kakao_shared: true,
        shared_by_user_at: nowIso,
        last_share_channel: shareChannel,
        updated_at: nowIso
      }
      pendingMessages.value.splice(pendingIdx, 1)
      historyMessages.value.unshift(foundMsg)
    } else {
      const historyIdx = historyMessages.value.findIndex((m) => m.id === messageId)
      if (historyIdx !== -1) {
        foundMsg = {
          ...historyMessages.value[historyIdx],
          status: 'shared',
          kakao_shared: true,
          shared_by_user_at: nowIso,
          last_share_channel: shareChannel,
          updated_at: nowIso
        }
        historyMessages.value[historyIdx] = foundMsg
      }
    }

    if (selectedMessage.value && selectedMessage.value.id === messageId && foundMsg) {
      selectedMessage.value = foundMsg
    }

    if (foundMsg && localMessages.value.some(m => m.id === messageId)) {
      persistLocal(localMessages.value.map(m => m.id === messageId ? foundMsg! : m))
      return foundMsg
    }

    // Call backend endpoint to persist
    try {
      const res = await api.markMessageShared(messageId, shareChannel)
      if (res && res.message) {
        return res.message
      }
    } catch (err) {
      console.warn('Backend mark-shared call failed (local state updated):', err)
    }

    return foundMsg
  }

  async function updateMessage(
    messageId: string,
    payload: { title?: string; body?: string }
  ): Promise<ShareMessage | null> {
    try {
      const res = await api.updateShareMessage(messageId, payload)
      const updated = res.share_message || res
      if (updated) {
        const pIdx = pendingMessages.value.findIndex((m) => m.id === messageId)
        if (pIdx !== -1) {
          pendingMessages.value[pIdx] = { ...pendingMessages.value[pIdx], ...updated }
        }

        const hIdx = historyMessages.value.findIndex((m) => m.id === messageId)
        if (hIdx !== -1) {
          historyMessages.value[hIdx] = { ...historyMessages.value[hIdx], ...updated }
        }

        if (selectedMessage.value?.id === messageId) {
          selectedMessage.value = { ...selectedMessage.value, ...updated }
        }
        return updated
      }
    } catch (err: any) {
      console.warn('Backend update-message call failed:', err)
      throw err
    }
    return null
  }

  return {
    deleteMessage,
    storageWarning,
    upsertLocalMessage,
    pendingMessages,
    historyMessages,
    selectedMessage,
    loading,
    refreshing,
    error,
    pendingCount,
    historyCount,
    fetchAll,
    fetchPending,
    fetchHistory,
    fetchById,
    markAsShared,
    updateMessage,
    clearError
  }
})
