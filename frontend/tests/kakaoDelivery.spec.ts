import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { beginKakaoDelivery, checkKakaoDeliveries, forgetKakaoDelivery } from '@/services/kakaoDelivery'
import { setActivePinia, createPinia } from 'pinia'
import { useMessagesStore } from '@/stores/messages'

beforeEach(() => localStorage.clear())
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
describe('Kakao delivery confirmation', () => {
  it('moves a local card to confirmed History and persists it only after delivery', async () => {
    setActivePinia(createPinia())
    const store = useMessagesStore()
    store.upsertLocalMessage({ id: 'receipt-local', endpoint_id: 'endpoint', title: 'Lesson', body: 'Body', status: 'pending', created_at: '', updated_at: '' })
    beginKakaoDelivery('receipt-local')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ delivered: true }))))
    await checkKakaoDeliveries(async id => !!await store.markAsShared(id, 'kakao_verified_webhook'))
    expect(store.pendingMessages.some(m => m.id === 'receipt-local')).toBe(false)
    expect(store.historyMessages.find(m => m.id === 'receipt-local')).toMatchObject({ kakao_shared: true, status: 'shared', last_share_channel: 'kakao_verified_webhook' })
    expect(localStorage.getItem('moatok_local_fetched_messages_v1')).toContain('kakao_verified_webhook')
  })
  it('waits for verified delivery and retries after a network failure', async () => {
    const id = beginKakaoDelivery('local_card')
    expect(id).toMatch(/^[a-f0-9]{64}$/)
    const confirm = vi.fn().mockResolvedValue(true)
    const fetch = vi.fn().mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ delivered: false })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ delivered: true })))
    vi.stubGlobal('fetch', fetch)
    await checkKakaoDeliveries(confirm)
    await checkKakaoDeliveries(confirm)
    expect(confirm).not.toHaveBeenCalled()
    await checkKakaoDeliveries(confirm)
    expect(confirm).toHaveBeenCalledWith('local_card')
    expect(localStorage.getItem('moatok_kakao_delivery_receipts_v1')).toBe('[]')
    await checkKakaoDeliveries(confirm)
    expect(fetch).toHaveBeenCalledTimes(3)
  })
  it('does not confirm on an unconfigured server or after an SDK error', async () => {
    const id = beginKakaoDelivery('card')
    const confirm = vi.fn()
    const fetch = vi.fn().mockResolvedValue(new Response('{}', { status: 503 }))
    vi.stubGlobal('fetch', fetch)
    await checkKakaoDeliveries(confirm)
    expect(confirm).not.toHaveBeenCalled()
    forgetKakaoDelivery(id)
    fetch.mockClear()
    await checkKakaoDeliveries(confirm)
    expect(fetch).not.toHaveBeenCalled()
  })
})
