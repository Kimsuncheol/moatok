import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest'
import { loginWithKakao } from '@/services/kakaoLogin'
vi.mock('@/services/api', () => ({ getApiBaseUrl: () => '' }))
beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })
describe('Kakao Firebase login', () => {
  it('rejects a blocked popup', async () => {
    vi.spyOn(window, 'open').mockReturnValue(null)
    await expect(loginWithKakao()).rejects.toThrow('팝업')
  })
  it('accepts only the expected popup and origin', async () => {
    vi.spyOn(window, 'open').mockReturnValue(window)
    vi.spyOn(window, 'close').mockImplementation(() => {})
    const promise = loginWithKakao()
    const result = vi.fn()
    promise.then(result)
    window.dispatchEvent(new MessageEvent('message', { source: window, origin: 'https://untrusted.example', data: { type: 'moatok-kakao-login', firebase_token: 'wrong' } }))
    await Promise.resolve()
    expect(result).not.toHaveBeenCalled()
    window.dispatchEvent(new MessageEvent('message', { source: window, origin: window.location.origin, data: { type: 'moatok-kakao-login', firebase_token: 'verified' } }))
    await expect(promise).resolves.toBe('verified')
    expect(window.close).toHaveBeenCalled()
  })
  it('reports provider errors and cleans up the popup', async () => {
    vi.spyOn(window, 'open').mockReturnValue(window)
    vi.spyOn(window, 'close').mockImplementation(() => {})
    const promise = loginWithKakao()
    window.dispatchEvent(new MessageEvent('message', { source: window, origin: window.location.origin, data: { type: 'moatok-kakao-login', error: '취소되었습니다' } }))
    await expect(promise).rejects.toThrow('취소되었습니다')
    expect(window.close).toHaveBeenCalled()
  })
})
