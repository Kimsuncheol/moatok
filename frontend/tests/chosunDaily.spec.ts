import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { CHOSUN_ARTICLES_URL } from '@/services/chosunDaily'
import { useEndpointsStore } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'
import { api } from '@/services/api'

beforeEach(() => { localStorage.clear(); setActivePinia(createPinia()) })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
it.each([true, false])('persists manual=%s fetches before displaying server cards', async manual => {
  const items = Array.from({ length: 10 }, (_, id) => ({ id, title: `Title ${id}`, body: `Body ${id}`, url: `https://www.chosun.com/english/${id}/` }))
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items }) }))
  const save = vi.spyOn(api, 'saveFetchedMessage').mockImplementation(async message => ({ message: { ...message, id: `import_${message.target_url}` } }))
  const endpoints = useEndpointsStore()
  const endpoint = endpoints.addEndpoint({ name: 'Chosun', url: CHOSUN_ARTICLES_URL, method: 'GET', sourceType: 'generic_api' })
  expect((await endpoints.triggerFetch(endpoint.id, manual)).success).toBe(true)
  expect(save).toHaveBeenCalledTimes(10)
  await endpoints.triggerFetch(endpoint.id, manual)
  const messages = useMessagesStore().pendingMessages.filter(m => m.endpoint_id === endpoint.id)
  expect(messages).toHaveLength(10)
  expect(messages.every(m => m.id.startsWith('import_'))).toBe(true)
  expect(localStorage.getItem('moatok_local_fetched_messages_v1')).not.toContain('Title')
})
it('reports a failed Firestore save instead of a successful fetch', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [{ id: 1, title: 'Article', body: 'Text', url: 'https://www.chosun.com/english/1/' }] }) }))
  vi.spyOn(api, 'saveFetchedMessage').mockRejectedValue(new Error('Save failed'))
  const endpoints = useEndpointsStore()
  const endpoint = endpoints.addEndpoint({ name: 'Chosun', url: CHOSUN_ARTICLES_URL, method: 'GET', sourceType: 'generic_api' })
  expect((await endpoints.triggerFetch(endpoint.id, true)).success).toBe(false)
  expect(useMessagesStore().pendingMessages.filter(m => m.fetch_status === 'success')).toHaveLength(0)
})
