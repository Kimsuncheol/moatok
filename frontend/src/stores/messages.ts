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

export const useMessagesStore = defineStore('messages', () => {
  const pendingMessages = ref<ShareMessage[]>([...SAMPLE_INITIAL_MESSAGES])
  const historyMessages = ref<ShareMessage[]>([])
  const selectedMessage = ref<ShareMessage | null>(null)
  const loading = ref<boolean>(false)
  const refreshing = ref<boolean>(false)
  const error = ref<string | null>(null)

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
        pendingMessages.value = res.messages
      }
    } catch (err: any) {
      console.warn('API fetch pending messages failed:', err)
      error.value = err.message || '공유 대기 메시지를 불러오지 못했습니다.'
    } finally {
      loading.value = false
      refreshing.value = false
    }
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
        pendingMessages.value = pendingRes.messages
      }

      // 2. Fetch history (shared) messages
      const historyRes = await api.getHistoryMessages()
      if (historyRes && Array.isArray(historyRes.messages)) {
        historyMessages.value = historyRes.messages
      }
    } catch (err: any) {
      console.warn('API fetch failed, retaining existing messages:', err)
      error.value = err.message || '메시지 목록을 불러오지 못했습니다.'
    } finally {
      loading.value = false
      refreshing.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  async function fetchById(messageId: string): Promise<ShareMessage | null> {
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
    fetchById,
    markAsShared,
    updateMessage,
    clearError
  }
})
