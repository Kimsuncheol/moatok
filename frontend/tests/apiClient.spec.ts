import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  api,
  ApiError,
  setTokenProvider,
  setOnSessionExpired,
  getApiBaseUrl,
  setApiBaseUrl
} from '@/services/api'

describe('API Client & Token Interceptor', () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    setApiBaseUrl('http://test-api.example.com')
    setTokenProvider(null)
    setOnSessionExpired(null)
    vi.restoreAllMocks()
  })

  afterEach(() => {
    global.fetch = originalFetch
    setApiBaseUrl(null)
    setTokenProvider(null)
    setOnSessionExpired(null)
  })

  it('respects API base URL configuration and trims trailing slashes', () => {
    setApiBaseUrl('https://custom-api.example.com///')
    expect(getApiBaseUrl()).toBe('https://custom-api.example.com')
  })

  it('injects Authorization: Bearer token when tokenProvider is set', async () => {
    let capturedHeaders: Headers | undefined
    setTokenProvider(async () => 'firebase-test-token-123')

    global.fetch = vi.fn().mockImplementation((_url, init) => {
      capturedHeaders = new Headers(init.headers)
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ user: { uid: 'u1', role: 'user', is_admin: false, email: 'u1@example.com' } })
      } as Response)
    })

    const res = await api.getProfile()
    expect(res.user.uid).toBe('u1')
    expect(capturedHeaders?.get('Authorization')).toBe('Bearer firebase-test-token-123')
    expect(capturedHeaders?.get('Content-Type')).toBe('application/json')
  })

  it('handles expired token (401 token_expired), forces refresh and retries successfully', async () => {
    let callCount = 0
    const tokenProviderSpy = vi.fn().mockImplementation(async (forceRefresh?: boolean) => {
      if (forceRefresh) {
        return 'refreshed-firebase-token-456'
      }
      return 'initial-expired-token-123'
    })
    setTokenProvider(tokenProviderSpy)

    const capturedAuthHeaders: string[] = []

    global.fetch = vi.fn().mockImplementation((_url, init) => {
      callCount++
      const headers = new Headers(init.headers)
      capturedAuthHeaders.push(headers.get('Authorization') || '')

      if (callCount === 1) {
        // First attempt fails with 401 token_expired
        return Promise.resolve({
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
          clone: () => ({
            json: async () => ({
              error: 'unauthorized',
              code: 'token_expired',
              message: 'Firebase ID token has expired.'
            })
          }),
          json: async () => ({
            error: 'unauthorized',
            code: 'token_expired',
            message: 'Firebase ID token has expired.'
          })
        } as unknown as Response)
      }

      // Second attempt (retry) succeeds with refreshed token
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ messages: [], count: 0 })
      } as unknown as Response)
    })

    const result = await api.getPendingMessages()
    expect(callCount).toBe(2)
    expect(tokenProviderSpy).toHaveBeenCalledWith(true) // Verified force refresh
    expect(capturedAuthHeaders[0]).toBe('Bearer initial-expired-token-123')
    expect(capturedAuthHeaders[1]).toBe('Bearer refreshed-firebase-token-456')
    expect(result.count).toBe(0)
  })

  it('invokes onSessionExpired when 401 cannot be recovered with refresh', async () => {
    const expiredHandler = vi.fn()
    setOnSessionExpired(expiredHandler)

    // Token refresh returns null (session permanently revoked)
    setTokenProvider(async (forceRefresh?: boolean) => {
      if (forceRefresh) return null
      return 'stale-token'
    })

    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        clone: () => ({
          json: async () => ({
            error: 'unauthorized',
            code: 'token_expired',
            message: 'Firebase ID token has expired.'
          })
        }),
        json: async () => ({
          error: 'unauthorized',
          code: 'token_expired',
          message: 'Firebase ID token has expired.'
        })
      } as unknown as Response)
    })

    await expect(api.getPendingMessages()).rejects.toThrow(ApiError)
    expect(expiredHandler).toHaveBeenCalledTimes(1)
    const errArg = expiredHandler.mock.calls[0][0]
    expect(errArg.status).toBe(401)
    expect(errArg.code).toBe('token_expired')
  })

  it('parses error payloads with statusText fallback when response is not JSON', async () => {
    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => {
          throw new Error('Not JSON')
        }
      } as unknown as Response)
    })

    await expect(api.getAllMessages()).rejects.toThrow('API Error [500]: Internal Server Error')
  })

  it('correctly constructs payloads for markMessageShared and registerFcmDevice', async () => {
    let capturedUrl = ''
    let capturedBody = ''
    let capturedMethod = ''

    global.fetch = vi.fn().mockImplementation((url, init) => {
      capturedUrl = url
      capturedMethod = init.method || 'GET'
      capturedBody = init.body
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ message: 'success', device_id: 'dev_123' })
      } as Response)
    })

    await api.markMessageShared('smsg_100', 'kakaotalk_web_pwa')
    expect(capturedUrl).toBe('http://test-api.example.com/api/v1/messages/smsg_100/mark-shared')
    expect(capturedMethod).toBe('POST')
    expect(JSON.parse(capturedBody)).toEqual({ share_channel: 'kakaotalk_web_pwa' })

    await api.registerFcmDevice({
      fcm_token: 'fcm_tok_abc',
      device_id: 'dev_iphone',
      platform: 'ios'
    })
    expect(capturedUrl).toBe('http://test-api.example.com/api/v1/devices/fcm-token')
    expect(JSON.parse(capturedBody)).toEqual({
      fcm_token: 'fcm_tok_abc',
      device_id: 'dev_iphone',
      platform: 'ios'
    })

    await api.reportShareAttempt('smsg_100', { channel: 'kakao_sdk' })
    expect(capturedUrl).toBe('http://test-api.example.com/api/v1/messages/smsg_100/share-attempt')
    expect(capturedMethod).toBe('POST')
    expect(JSON.parse(capturedBody)).toEqual({ channel: 'kakao_sdk' })

    await api.updateShareMessage('smsg_100', {
      body: '수정된 브리핑 문구'
    })
    expect(capturedUrl).toBe('http://test-api.example.com/api/v1/admin/share-messages/smsg_100')
    expect(capturedMethod).toBe('PATCH')
    expect(JSON.parse(capturedBody)).toEqual({
      body: '수정된 브리핑 문구'
    })
  })
  it('reports a missing backend when Hosting returns the app HTML', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('<!DOCTYPE html><html></html>', {
      status: 200, headers: { 'Content-Type': 'text/html' }
    }))
    await expect(api.getProfile()).rejects.toMatchObject({ code: 'backend_not_configured', status: 503 })
  })

})
