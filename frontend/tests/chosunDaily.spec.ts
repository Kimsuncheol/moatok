import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { CHOSUN_ARTICLES_URL } from '@/services/chosunDaily'
import { useEndpointsStore } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'

describe('Chosun Daily import', () => {
  beforeEach(() => { localStorage.clear(); setActivePinia(createPinia()) })
  afterEach(() => vi.unstubAllGlobals())
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
