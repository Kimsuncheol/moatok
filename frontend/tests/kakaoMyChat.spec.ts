import { initKakaoSdk, loadKakaoSdkScript } from '@/services/kakao'
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { buildMyChatTemplate, sendToMyChat, connectMyChat, clearMyChatConnection } from '@/services/kakaoMyChat'
import type { ShareMessage } from '@/types'
vi.mock('@/services/kakao', () => ({loadKakaoSdkScript: vi.fn().mockResolvedValue(true), initKakaoSdk: vi.fn().mockReturnValue(true)}))
const message = {id:'card', title:'Test', body:'Lesson content'} as ShareMessage
afterEach(() => { clearMyChatConnection(); vi.restoreAllMocks() })
describe('Kakao My Chat', () => {
  beforeEach(() => { vi.mocked(loadKakaoSdkScript).mockResolvedValue(true); vi.mocked(initKakaoSdk).mockReturnValue(true) })
  it('uses the official text template with a registered home link', () => {
    const result = buildMyChatTemplate(message)
    expect(result.object_type).toBe('text')
    expect(result.text).toBe(message.body)
    expect(result.link.web_url).toBe(window.location.origin + '/')
    expect(result).not.toHaveProperty('receiver_uuids')
  })
  it('bounds the text to 200 characters and rejects empty messages', () => {
    expect(buildMyChatTemplate({...message, body:'a'.repeat(500)}).text.length).toBe(200)
    expect(() => buildMyChatTemplate({...message, body:' '})).toThrow()
  })
  it('never sends without a connected account', async () => {
    const request = vi.fn()
    window.Kakao = {init:vi.fn(), isInitialized:()=>true, Share:{sendDefault:vi.fn(), sendCustom:vi.fn()}, API:{request}, Auth:{setAccessToken:vi.fn()}}
    await expect(sendToMyChat(message)).rejects.toThrow('연결')
    expect(request).not.toHaveBeenCalled()
  })
  it('reports blocked popups', async () => {
    vi.spyOn(window, 'open').mockReturnValue(null)
    await expect(connectMyChat()).rejects.toThrow('팝업')
  })
  it('reports an undeployed backend instead of parsing Hosting HTML', async () => {
    const close = vi.fn()
    vi.spyOn(window, 'open').mockReturnValue({close} as unknown as Window)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', {headers:{'Content-Type':'text/html'}})))
    await expect(connectMyChat()).rejects.toThrow('서버')
    expect(close).toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
  it('connects only from the expected popup and sends only to memo/default/send', async () => {
    vi.spyOn(window, 'open').mockReturnValue(window)
    vi.spyOn(window, 'close').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({configured:true}), {headers:{'Content-Type':'application/json'}})))
    const pending = connectMyChat()
    await new Promise(resolve => setTimeout(resolve, 10))
    window.dispatchEvent(new MessageEvent('message', {origin:window.location.origin, source:window,
      data:{type:'moatok-kakao-login', access_token:'test-token', expires_in:3600}}))
    await pending
    const request = vi.fn().mockResolvedValue({result_code:0})
    window.Kakao = {init:vi.fn(), isInitialized:()=>true, Share:{sendDefault:vi.fn(), sendCustom:vi.fn()}, API:{request}, Auth:{setAccessToken:vi.fn()}}
    await sendToMyChat(message)
    expect(request).toHaveBeenCalledWith({url:'/v2/api/talk/memo/default/send', data:{template_object:buildMyChatTemplate(message)}})
    request.mockRejectedValueOnce({code:-402})
    await expect(sendToMyChat(message)).rejects.toThrow('동의')
    await expect(sendToMyChat(message)).rejects.toThrow('연결')
    expect(request).toHaveBeenCalledTimes(2)
    vi.unstubAllGlobals()
  })

})
