import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MessageDetailView from '@/views/MessageDetailView.vue'
import { useMessagesStore } from '@/stores/messages'
import { useAuthStore } from '@/stores/auth'
import * as kakaoService from '@/services/kakao'
import type { ShareMessage } from '@/types'

const mockRouterPush = vi.fn()
const mockRouterBack = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    back: mockRouterBack
  })
}))

vi.mock('@/services/kakao', () => ({
  initiateKakaoShare: vi.fn(),
  initKakaoSdk: vi.fn(() => false)
}))

describe('MessageDetailView Component', () => {
  const sampleMessage: ShareMessage = {
    id: 'smsg_detail_1',
    article_id: 'art_123',
    title: '클라우드 보안 및 IAM 최소 권한 가이드',
    body: '[모아톡 브리핑] 클라우드 보안 가이드입니다.\n\n🔗 https://feeds.example.com/security',
    target_url: 'https://feeds.example.com/security',
    source_name: '보안 뉴스레터',
    status: 'pending',
    kakao_shared: false,
    created_at: '2026-11-06T00:15:00Z',
    updated_at: '2026-11-06T00:15:00Z'
  }

  it.each(['status', 'fetch_status'])('disables sharing actions for failed %s', async (field) => {
    const store = useMessagesStore()
    vi.spyOn(store, 'fetchById').mockResolvedValue({ ...sampleMessage, [field]: 'failed' })
    const wrapper = mount(MessageDetailView, { props: { id: sampleMessage.id } })
    await new Promise(resolve => setTimeout(resolve, 10))
    const buttons = wrapper.findAll('.action-buttons-group button:not(.pending-detail-delete)')
    expect(buttons).toHaveLength(2)
    for (const button of buttons) expect(button.attributes('disabled')).toBeDefined()
  })

  it('keeps Fetch enabled on failed endpoint messages while sharing stays disabled', async () => {
    const store = useMessagesStore()
    vi.spyOn(store, 'fetchById').mockResolvedValue({ ...sampleMessage, status: 'failed', endpoint_id: 'endpoint-test' })
    const wrapper = mount(MessageDetailView, { props: { id: sampleMessage.id } })
    await new Promise(resolve => setTimeout(resolve, 10))
    const fetchButton = wrapper.find('.fetch-action-btn')
    expect(fetchButton.text()).toContain('Fetch')
    expect(fetchButton.attributes('disabled')).toBeUndefined()
    expect(wrapper.find('.mark-shared-btn').attributes('disabled')).toBeDefined()
  })

  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouterPush.mockReset()
    mockRouterBack.mockReset()
    vi.restoreAllMocks()

    vi.mocked(kakaoService.initiateKakaoShare).mockResolvedValue({
      success: true,
      channel: 'kakao_sdk',
      notice: '카카오톡 공유 창이 열렸습니다. 대상 채팅방을 선택해주세요.'
    })
  })

  it('renders article title, share text, source name, original article URL, creation time, and status', async () => {
    const messagesStore = useMessagesStore()
    vi.spyOn(messagesStore, 'fetchById').mockResolvedValue(sampleMessage)

    const wrapper = mount(MessageDetailView, {
      props: {
        id: 'smsg_detail_1'
      }
    })

    // Wait for onMounted fetch
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 10))
    await wrapper.vm.$nextTick()

    // 1. Article title
    expect(wrapper.find('.article-title').text()).toBe('클라우드 보안 및 IAM 최소 권한 가이드')

    // 2. Share text
    expect(wrapper.find('.share-text-content').text()).toBe(sampleMessage.body)

    // 3. Source name
    expect(wrapper.find('.source-badge').text()).toContain('보안 뉴스레터')

    // 4. Original article URL
    const urlEl = wrapper.find('.article-url-section a.url-link')
    expect(urlEl.exists()).toBe(true)
    expect(urlEl.attributes('href')).toBe('https://feeds.example.com/security')

    // 5. Creation time
    expect(wrapper.find('.creation-time').exists()).toBe(true)

    // 6. Current share status
    expect(wrapper.find('.status-badge').text()).toBe('공유 대기')

    // 7. Policy and Open Chat real-device advisory
    const policyNotice = wrapper.find('.sharing-policy-notice')
    expect(policyNotice.exists()).toBe(true)
    expect(policyNotice.text()).toContain('사용자 주도 전송 원칙')
    expect(policyNotice.text()).toContain('오픈채팅방 지원 안내')
    expect(policyNotice.text()).toContain('실제 모바일 기기')
  })

  it('hides admin edit button for regular non-admin users', async () => {
    const messagesStore = useMessagesStore()
    const authStore = useAuthStore()
    authStore.profile = { uid: 'u1', email: 'u1@example.com', role: 'user', is_admin: false }
    vi.spyOn(messagesStore, 'fetchById').mockResolvedValue(sampleMessage)

    const wrapper = mount(MessageDetailView, {
      props: { id: 'smsg_detail_1' }
    })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 10))

    expect(wrapper.find('.admin-edit-btn').exists()).toBe(false)
  })

  it('allows administrators to edit share text and save changes via API', async () => {
    const messagesStore = useMessagesStore()
    const authStore = useAuthStore()
    authStore.profile = { uid: 'admin_1', email: 'admin@example.com', role: 'admin', is_admin: true }
    vi.spyOn(messagesStore, 'fetchById').mockResolvedValue(sampleMessage)

    const updateSpy = vi.spyOn(messagesStore, 'updateMessage').mockResolvedValue({
      ...sampleMessage,
      body: '관리자가 수정한 브리핑 내용입니다.'
    })

    const wrapper = mount(MessageDetailView, {
      props: { id: 'smsg_detail_1' }
    })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 10))
    await wrapper.vm.$nextTick()

    // Admin edit button should be visible
    const editBtn = wrapper.find('.admin-edit-btn')
    expect(editBtn.exists()).toBe(true)

    // Click edit button
    await editBtn.trigger('click')
    expect(wrapper.find('.edit-form-card').exists()).toBe(true)

    // Modify textarea
    const textarea = wrapper.find('.field-textarea')
    await textarea.setValue('관리자가 수정한 브리핑 내용입니다.')

    // Click save
    await wrapper.find('.save-btn').trigger('click')

    expect(updateSpy).toHaveBeenCalledWith('smsg_detail_1', {
      title: '클라우드 보안 및 IAM 최소 권한 가이드',
      body: '관리자가 수정한 브리핑 내용입니다.'
    })

    // Edit mode closes and updated content is displayed
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.edit-form-card').exists()).toBe(false)
    expect(wrapper.find('.share-text-content').text()).toBe('관리자가 수정한 브리핑 내용입니다.')
    expect(wrapper.find('.success-banner').exists()).toBe(true)
  })

  it('delegates to initiateKakaoShare and DOES NOT label message as delivered merely upon button click', async () => {
    const messagesStore = useMessagesStore()
    vi.spyOn(messagesStore, 'fetchById').mockResolvedValue(sampleMessage)
    const markSharedSpy = vi.spyOn(messagesStore, 'markAsShared')

    const wrapper = mount(MessageDetailView, {
      props: { id: 'smsg_detail_1' }
    })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 10))
    await wrapper.vm.$nextTick()

    // 1. Click the prominent Kakao Share button
    const kakaoBtn = wrapper.find('.prominent-kakao-btn')
    expect(kakaoBtn.exists()).toBe(true)
    await kakaoBtn.trigger('click')

    // Verified: Kakao service function was invoked
    expect(kakaoService.initiateKakaoShare).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'smsg_detail_1' })
    )

    // CRITICAL REQUIREMENT VERIFICATION:
    // Merely clicking the share button MUST NOT mark the message as delivered or shared!
    expect(markSharedSpy).not.toHaveBeenCalled()
    expect(wrapper.find('.status-badge').text()).toBe('공유 대기')

    // Outcome feedback is displayed instructing user
    expect(wrapper.find('.share-feedback-notice').text()).toContain(
      '카카오톡 공유 창이 열렸습니다'
    )

    // 2. Explicit confirmation: User taps '카카오톡 전송 완료로 기록하기'
    const confirmBtn = wrapper.find('.mark-shared-btn')
    expect(confirmBtn.exists()).toBe(true)

    markSharedSpy.mockResolvedValue({
      ...sampleMessage,
      status: 'shared',
      kakao_shared: true,
      shared_by_user_at: new Date().toISOString()
    })

    await confirmBtn.trigger('click')

    // Now markAsShared is called explicitly
    expect(markSharedSpy).toHaveBeenCalledWith('smsg_detail_1', 'kakaotalk_web_pwa')
    await wrapper.vm.$nextTick()

    // Status updates to shared
    expect(wrapper.find('.status-badge').text()).toBe('카카오톡 공유 완료')
  })
})
