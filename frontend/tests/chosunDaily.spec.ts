import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { CHOSUN_ARTICLES_URL } from '@/services/chosunDaily'
import { useEndpointsStore } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'
import { api } from '@/services/api'

describe('Chosun Daily import', () => {
  beforeEach(() => { localStorage.clear(); setActivePinia(createPinia()) })
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
  it('restores manually re-fetched deleted articles while preserving shared History through reload', async () => {
    const items = Array.from({ length: 10 }, (_, id) => ({ id, title: `Title ${id}`, body: `Body ${id}`, url: `https://www.chosun.com/english/${id}/` }))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items }) }))
    const endpoints = useEndpointsStore()
    const endpoint = endpoints.addEndpoint({ name: 'Chosun', url: CHOSUN_ARTICLES_URL, method: 'GET', sourceType: 'generic_api' })
    await endpoints.triggerFetch(endpoint.id, true)
    const store = useMessagesStore()
    const imported = [...store.pendingMessages]
    for (const card of imported.slice(0, 2)) await store.markAsShared(card.id)
    for (const card of imported.slice(2)) store.deleteMessage(card.id)
    expect(store.pendingCount).toBe(0)

    const automatic = await endpoints.triggerFetch(endpoint.id, false)
    expect(automatic.message).toContain('공유 대기 0개')
    expect(store.pendingCount).toBe(0)
    const manual = await endpoints.triggerFetch(endpoint.id, true)
    expect(manual.message).toContain('공유 대기 8개')
    expect(manual.message).toContain('이미 공유됨 2개')
    expect(store.pendingCount).toBe(8)
    expect(store.historyCount).toBe(2)
    vi.spyOn(api, 'getPendingMessages').mockResolvedValue({ messages: [], count: 0 })
    await store.fetchPending(true)
    expect(store.pendingCount).toBe(8)
    setActivePinia(createPinia())
    const restored = useMessagesStore()
    expect(restored.pendingCount).toBe(8)
    expect(restored.historyCount).toBe(2)
    expect(await restored.fetchById(imported[2].id)).toMatchObject({ status: 'pending' })
  })
  it('imports individual articles through the proxy and deduplicates repeated fetches', async () => {
    const items = Array.from({ length: 10 }, (_, id) => ({ id, title: `Title ${id}`, body: `Body ${id}`, url: `https://www.chosun.com/english/${id}/` }))
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items }) })
    vi.stubGlobal('fetch', fetch)
    const endpoints = useEndpointsStore()
    const endpoint = endpoints.addEndpoint({ name: 'Chosun', url: CHOSUN_ARTICLES_URL, method: 'GET', sourceType: 'generic_api' })
    await endpoints.triggerFetch(endpoint.id, true)
    await endpoints.triggerFetch(endpoint.id, true)
    expect(fetch.mock.calls[0][0]).toContain('/api/v1/integrations/chosun-daily/articles')
    const messages = useMessagesStore().pendingMessages.filter(m => m.endpoint_id === endpoint.id)
    expect(messages).toHaveLength(10)
    expect(messages.find(m => m.title === 'Title 0')).toMatchObject({ body: 'Body 0', target_url: items[0].url })
  })
})
