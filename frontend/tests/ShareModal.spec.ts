import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ShareModal from '@/components/ShareModal.vue'
import * as kakaoService from '@/services/kakao'
import { api } from '@/services/api'
import type { ShareMessage } from '@/types'

const dummyMessage: ShareMessage = {
  id: 'test-msg-1',
  title: 'Test Briefing Title',
  body: '[모아톡 브리핑] Test Briefing Title\n\nShort summary of test briefing.',
  target_url: 'https://example.com/test',
  status: 'pending',
  kakao_shared: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
}

describe('ShareModal Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('displays the user-initiated sharing advisory clearly', () => {
    const wrapper = mount(ShareModal, {
      props: {
        modelValue: true,
        message: dummyMessage
      }
    })

    const noticeBanner = wrapper.find('.notice-banner')
    expect(noticeBanner.exists()).toBe(true)

    // Critical constraint: Must not claim automatic posting to Open Chat
    const noticeText = noticeBanner.text()
    expect(noticeText).toContain('사용자 직접 공유 원칙')
    expect(noticeText).toContain('자동으로 게시하지 않습니다')
    expect(noticeText).toContain('직접 선택')
  })

  it('invokes initiateKakaoShare and emits shared event on button click', async () => {
    vi.spyOn(kakaoService, 'initiateKakaoShare').mockResolvedValue({
      success: true,
      channel: 'clipboard',
      notice: '클립보드에 복사되었습니다.'
    })
    vi.spyOn(api, 'markMessageShared').mockResolvedValue({
      message: {
        ...dummyMessage,
        status: 'shared',
        kakao_shared: true,
        shared_by_user_at: new Date().toISOString()
      }
    })

    const wrapper = mount(ShareModal, {
      props: {
        modelValue: true,
        message: dummyMessage
      }
    })

    const shareBtn = wrapper.find('.share-primary-btn')
    expect(shareBtn.exists()).toBe(true)
    await shareBtn.trigger('click')
    await flushPromises()

    expect(kakaoService.initiateKakaoShare).toHaveBeenCalledWith(dummyMessage)
    expect(wrapper.emitted('shared')).toBeTruthy()
  })
})
