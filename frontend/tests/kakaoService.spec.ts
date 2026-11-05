import { describe, it, expect, beforeEach, vi } from 'vitest'
import { initiateKakaoShare } from '@/services/kakao'
import type { ShareMessage } from '@/types'

const sampleMessage: ShareMessage = {
  id: 'kakao-test-msg',
  title: 'Kakao Test Article',
  body: '[모아톡 브리핑] Kakao Test Article\n\nDetailed test body.',
  target_url: 'https://example.com/kakao-test',
  status: 'pending',
  kakao_shared: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
}

describe('Kakao Share Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('falls back to clipboard copy when neither Kakao SDK nor Web Share is available', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock
      },
      share: undefined
    })

    const result = await initiateKakaoShare(sampleMessage)
    expect(result.success).toBe(true)
    expect(result.channel).toBe('clipboard')
    expect(writeTextMock).toHaveBeenCalledWith(sampleMessage.body)
    expect(result.notice).toContain('클립보드에 복사되었습니다')
    expect(result.notice).toContain('원하는 채팅방에 붙여넣어 공유')
  })

  it('uses Web Share API if supported and returns explicit user instruction', async () => {
    const shareMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      share: shareMock
    })

    const result = await initiateKakaoShare(sampleMessage)
    expect(result.success).toBe(true)
    expect(result.channel).toBe('web_share')
    expect(shareMock).toHaveBeenCalledWith({
      title: sampleMessage.title,
      text: sampleMessage.body,
      url: sampleMessage.target_url
    })
    expect(result.notice).toContain('카카오톡 및 대상 채팅방을 직접 선택')
  })

  it('uses Kakao SDK sendDefault when window.Kakao is initialized', async () => {
    const sendDefaultMock = vi.fn()
    ;(window as any).Kakao = {
      isInitialized: () => true,
      init: vi.fn(),
      Share: {
        sendDefault: sendDefaultMock
      }
    }

    const result = await initiateKakaoShare(sampleMessage)
    expect(result.success).toBe(true)
    expect(result.channel).toBe('kakao_sdk')
    expect(sendDefaultMock).toHaveBeenCalled()
    expect(result.notice).toContain('전송할 대상 채팅방을 직접 선택')
  })
})
