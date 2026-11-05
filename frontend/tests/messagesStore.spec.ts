import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMessagesStore } from '@/stores/messages'
import { api } from '@/services/api'
import type { ShareMessage } from '@/types'

describe('Messages Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('initializes with sample pending messages and correct counts', () => {
    const store = useMessagesStore()
    expect(store.pendingCount).toBeGreaterThanOrEqual(1)
    expect(store.historyCount).toBe(0)
  })

  it('fetches pending messages from API via fetchPending', async () => {
    const store = useMessagesStore()

    const mockPending: ShareMessage[] = [
      {
        id: 'smsg_fetched_1',
        title: '신규 수집된 브리핑',
        body: '내용입니다.',
        source_name: 'Tech News',
        status: 'pending',
        kakao_shared: false,
        created_at: '2026-11-06T00:00:00Z',
        updated_at: '2026-11-06T00:00:00Z'
      }
    ]

    vi.spyOn(api, 'getPendingMessages').mockResolvedValue({
      messages: mockPending,
      count: 1
    })

    await store.fetchPending()

    expect(api.getPendingMessages).toHaveBeenCalledTimes(1)
    expect(store.pendingCount).toBe(1)
    expect(store.pendingMessages[0].id).toBe('smsg_fetched_1')
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('handles API errors in fetchPending and sets error message', async () => {
    const store = useMessagesStore()

    vi.spyOn(api, 'getPendingMessages').mockRejectedValue(new Error('Network failure'))

    await store.fetchPending()

    expect(store.error).toBe('Network failure')
    expect(store.loading).toBe(false)

    store.clearError()
    expect(store.error).toBeNull()
  })

  it('marks a message as shared and moves it from pending to history', async () => {
    const store = useMessagesStore()
    const targetMsg = store.pendingMessages[0]
    expect(targetMsg).toBeDefined()
    const targetId = targetMsg.id

    vi.spyOn(api, 'markMessageShared').mockResolvedValue({
      message: {
        ...targetMsg,
        status: 'shared',
        kakao_shared: true,
        shared_by_user_at: new Date().toISOString(),
        last_share_channel: 'kakaotalk_test'
      }
    })

    const initialPending = store.pendingCount
    const initialHistory = store.historyCount

    const updated = await store.markAsShared(targetId, 'kakaotalk_test')
    expect(updated).not.toBeNull()
    expect(updated?.kakao_shared).toBe(true)
    expect(updated?.status).toBe('shared')
    expect(updated?.last_share_channel).toBe('kakaotalk_test')

    expect(store.pendingCount).toBe(initialPending - 1)
    expect(store.historyCount).toBe(initialHistory + 1)
    expect(store.historyMessages[0].id).toBe(targetId)
  })
})
