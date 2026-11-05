import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMessagesStore } from '@/stores/messages'
import { api } from '@/services/api'

describe('Messages Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with sample pending messages and correct counts', () => {
    const store = useMessagesStore()
    expect(store.pendingCount).toBeGreaterThanOrEqual(1)
    expect(store.historyCount).toBe(0)
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
