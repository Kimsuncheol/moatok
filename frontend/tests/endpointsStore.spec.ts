import { englishScraperApi } from '@/services/api'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEndpointsStore, DEFAULT_ENGLISH_SCRAPPER_URL } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'

describe('Endpoints Store', () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
  beforeEach(() => {
    setActivePinia(createPinia())
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear()
    }
  })

  it('initializes with default english_scrapper endpoint', () => {
    const store = useEndpointsStore()
    store.loadEndpoints()

    expect(store.endpoints.length).toBeGreaterThanOrEqual(1)
    const englishEp = store.endpoints.find((e) => e.sourceType === 'english_scrapper')
    expect(englishEp).toBeDefined()
    expect(englishEp?.url).toBe(DEFAULT_ENGLISH_SCRAPPER_URL + '/api/v1/lessons/fetch')
    expect(englishEp?.schedule.maxRetries).toBe(5)
    expect(englishEp?.schedule.retryIntervalHours).toBe(1)
  })

  it('adds and deletes an endpoint with valid schedule', () => {
    const store = useEndpointsStore()
    const endpoint = store.addEndpoint({
      name: 'Custom Service',
      url: 'https://api.myfeed.com/articles',
      method: 'GET',
      schedule: {
        scheduledTime: '10:00',
        maxRetries: 5,
        retryIntervalHours: 1
      }
    })

    expect(endpoint.id).toBeDefined()
    expect(endpoint.name).toBe('Custom Service')
    expect(endpoint.schedule.maxRetries).toBe(5)
    expect(store.endpoints.some((e) => e.id === endpoint.id)).toBe(true)

    store.deleteEndpoint(endpoint.id)
    expect(store.endpoints.some((e) => e.id === endpoint.id)).toBe(false)
  })

  it('rejects invalid URLs', () => {
    const store = useEndpointsStore()
    expect(() =>
      store.addEndpoint({
        name: 'Invalid',
        url: 'invalid-url-format'
      })
    ).toThrow('유효한 URL 형식이 아닙니다.')
  })

  it('records failed fetch attempts up to 5 and creates failed card in Pending view', async () => {
    const store = useEndpointsStore()
    const messagesStore = useMessagesStore()

    const ep = store.addEndpoint({
      name: 'Unreachable API',
      url: 'https://unreachable.invalid.domain/data'
    })

    // Simulate 5 attempts
    for (let i = 0; i < 5; i++) {
      await store.triggerFetch(ep.id, false)
    }

    expect(ep.schedule.currentAttempts).toBe(5)
    expect(ep.schedule.lastStatus).toBe('failed')

    // Verify card in pendingMessages
    const failedCard = messagesStore.pendingMessages.find((m) => m.endpoint_id === ep.id)
    expect(failedCard).toBeDefined()
    expect(failedCard?.status).toBe('failed')
    expect(failedCard?.fetch_status).toBe('failed')
    expect(failedCard?.title).toContain('[수집 실패]')
  })

  it('successfully fetches and places pending briefing card in Pending view', async () => {
    vi.spyOn(englishScraperApi, 'fetchUrl').mockResolvedValueOnce({status: 'fetched', lesson: {url: 'https://www.chosun.com/example/', fields: {expression: 'Actual lesson'}, missing_sections: []}})
    const store = useEndpointsStore()
    const messagesStore = useMessagesStore()

    const ep = store.addEndpoint({
      name: 'English Scraper API',
      url: DEFAULT_ENGLISH_SCRAPPER_URL,
      sourceType: 'english_scrapper'
    })

    const result = await store.triggerFetch(ep.id, true)
    expect(result.success).toBe(true)

    const message = messagesStore.pendingMessages.find((m) => m.endpoint_id === ep.id)
    expect(message).toBeDefined()
    expect(message?.status).toBe('pending')
    expect(message?.fetch_status).toBe('success')
    expect(message?.title).toBe('Actual lesson')
  })
  it('preserves complete API messages and sends the registered POST payload', async () => {
    const body = '수집된 메시지 '.repeat(100)
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ body }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    const store = useEndpointsStore()
    const endpoint = store.addEndpoint({ name: 'Messages', url: 'https://api.example.com/messages', method: 'POST', headers: { 'Content-Type': 'application/json' }, payload: '{"latest":true}' })
    const result = await store.triggerFetch(endpoint.id, true)
    expect(fetch).toHaveBeenCalledWith(endpoint.url, expect.objectContaining({ method: 'POST', body: '{"latest":true}' }))
    expect(result.shareMessage?.body).toBe(body)
    expect(result.shareMessage?.body.length).toBeGreaterThan(300)
  })
  it('preserves complete structured JSON when an API has no message field', async () => {
    const data = { articles: [{ text: 'Article '.repeat(100) }] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(data), { status: 200 })))
    const store = useEndpointsStore()
    const endpoint = store.addEndpoint({ name: 'Articles', url: 'https://api.example.com/articles' })
    const result = await store.triggerFetch(endpoint.id, true)
    expect(result.shareMessage?.body).toContain(JSON.stringify(data, null, 2))
  })

})
