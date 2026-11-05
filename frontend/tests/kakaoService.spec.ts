import { describe, it, expect, beforeEach, vi } from 'vitest'
import { initiateKakaoShare, getRegisteredMessageUrl } from '@/services/kakao'
import { api } from '@/services/api'
import type { ShareMessage } from '@/types'

const sampleMessage: ShareMessage = {
  id: 'kakao-test-msg',
  title: 'Kakao Test Article',
  body: '[모아톡 브리핑] Kakao Test Article\n\nDetailed test body.',
  target_url: 'https://external-news.example.com/kakao-test',
  status: 'pending',
  kakao_shared: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
}

describe('Kakao Share Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'reportShareAttempt').mockResolvedValue({
      message_id: 'kakao-test-msg',
      recorded: true,
      channel: 'test',
      share_attempt_count: 1
    })
  })

  it('generates the registered domain detail URL for Kakao template links', () => {
    const url = getRegisteredMessageUrl('msg-999')
    expect(url).toContain('/messages/msg-999')
    expect(url.startsWith('http')).toBe(true)
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
    expect(result.openChatNotice).toContain('실제 모바일 기기')
    expect(api.reportShareAttempt).toHaveBeenCalledWith(sampleMessage.id, { channel: 'clipboard' })
  })

  it('uses Web Share API with registered domain URL if supported and returns explicit user instruction', async () => {
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
      url: expect.stringContaining('/messages/kakao-test-msg')
    })
    expect(result.notice).toContain('대상 채팅방을 직접 선택')
    expect(result.openChatNotice).toContain('실제 모바일 기기')
    expect(api.reportShareAttempt).toHaveBeenCalledWith(sampleMessage.id, { channel: 'web_share' })
  })

  it('uses Kakao SDK sendDefault with registered domain URL when window.Kakao is initialized', async () => {
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
    expect(sendDefaultMock).toHaveBeenCalledWith({
      objectType: 'text',
      text: sampleMessage.body,
      link: {
        mobileWebUrl: expect.stringContaining('/messages/kakao-test-msg'),
        webUrl: expect.stringContaining('/messages/kakao-test-msg')
      },
      buttonTitle: '브리핑 상세 보기'
    })
    expect(result.notice).toContain('전송할 대상 채팅방을 직접 선택')
    expect(result.openChatNotice).toContain('실제 모바일 기기')
    expect(api.reportShareAttempt).toHaveBeenCalledWith(sampleMessage.id, { channel: 'kakao_sdk' })
  })

  it('supports feed template with image and registered domain links when payload specifies feed', async () => {
    const sendDefaultMock = vi.fn()
    ;(window as any).Kakao = {
      isInitialized: () => true,
      init: vi.fn(),
      Share: {
        sendDefault: sendDefaultMock
      }
    }

    const feedMessage: ShareMessage = {
      ...sampleMessage,
      kakao_share_payload: {
        template_type: 'feed',
        image_url: 'https://images.example.com/banner.jpg',
        description: 'Feed template short description',
        button_title: '자세히 보기'
      }
    }

    const result = await initiateKakaoShare(feedMessage)
    expect(result.success).toBe(true)
    expect(result.channel).toBe('kakao_sdk')
    expect(sendDefaultMock).toHaveBeenCalledWith(
      expect.objectContaining({
        objectType: 'feed',
        content: expect.objectContaining({
          title: feedMessage.title,
          description: 'Feed template short description',
          imageUrl: 'https://images.example.com/banner.jpg',
          link: expect.objectContaining({
            webUrl: expect.stringContaining('/messages/kakao-test-msg')
          })
        }),
        buttons: expect.arrayContaining([
          expect.objectContaining({
            title: '자세히 보기',
            link: expect.objectContaining({
              webUrl: expect.stringContaining('/messages/kakao-test-msg')
            })
          })
        ])
      })
    )
  })

  it('falls back to Web Share if Kakao SDK sendDefault throws an error', async () => {
    ;(window as any).Kakao = {
      isInitialized: () => true,
      init: vi.fn(),
      Share: {
        sendDefault: vi.fn().mockImplementation(() => {
          throw new Error('Kakao SDK KOE001 network error')
        })
      }
    }

    const shareMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      share: shareMock
    })

    const result = await initiateKakaoShare(sampleMessage)
    expect(result.success).toBe(true)
    expect(result.channel).toBe('web_share')
    expect(shareMock).toHaveBeenCalled()
    expect(api.reportShareAttempt).toHaveBeenCalledWith(sampleMessage.id, { channel: 'web_share' })
  })
})
