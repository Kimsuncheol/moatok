import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PendingView from '@/views/PendingView.vue'
import { useMessagesStore } from '@/stores/messages'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'
import type { ShareMessage } from '@/types'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush
  })
}))

describe('PendingView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.user = { uid: 'test-user' } as any
    auth.status = 'authenticated'
    auth.loading = false
    mockRouterPush.mockReset()
    vi.restoreAllMocks()
    vi.spyOn(api, 'getPendingMessages').mockResolvedValue({
      messages: [],
      count: 0
    })
  })

  it('waits for restored authentication before fetching protected messages', async () => {
    const auth = useAuthStore()
    auth.user = null
    auth.status = 'loading'
    auth.loading = true
    const fetch = vi.spyOn(useMessagesStore(), 'fetchPending').mockResolvedValue()
    const wrapper = mount(PendingView)
    expect(fetch).not.toHaveBeenCalled()
    auth.user = { uid: 'restored-user' } as any
    auth.status = 'authenticated'
    auth.loading = false
    await wrapper.vm.$nextTick()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('shows sign-in guidance without sending unauthenticated fetch requests', async () => {
    const auth = useAuthStore()
    auth.user = null
    auth.status = 'signed_out'
    const store = useMessagesStore()
    store.pendingMessages = []
    store.error = 'API Error [401]: Missing Authorization Bearer token.'
    const fetch = vi.spyOn(store, 'fetchPending').mockResolvedValue()
    const wrapper = mount(PendingView, { global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } })
    expect(wrapper.find('a[href="/settings/account"]').exists()).toBe(true)
    expect(wrapper.find('.error-state-card').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Missing Authorization')
    await wrapper.get('.refresh-action-btn').trigger('click')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('renders header, title, and count pill', () => {
    const store = useMessagesStore()
    const wrapper = mount(PendingView)

    expect(wrapper.find('.view-title').text()).toBe('공유 대기 브리핑')
    expect(wrapper.find('.count-pill').text()).toBe(`${store.pendingCount}건`)
  })

  it('displays skeleton loading state when store.loading is true', () => {
    const store = useMessagesStore()
    store.loading = true
    store.refreshing = false

    const wrapper = mount(PendingView)

    expect(wrapper.find('.loading-skeleton-list').exists()).toBe(true)
    expect(wrapper.findAll('.skeleton-card').length).toBe(3)
    expect(wrapper.find('.message-list').exists()).toBe(false)
  })

  it('displays error card and triggers retry when store.error is set', async () => {
    const store = useMessagesStore()
    store.loading = false
    store.error = '네트워크 연결 실패'

    const refreshSpy = vi.spyOn(store, 'fetchPending').mockResolvedValue()

    const wrapper = mount(PendingView)

    expect(wrapper.find('.error-state-card').exists()).toBe(true)
    expect(wrapper.find('.error-desc').text()).toBe('네트워크 연결 실패')

    await wrapper.find('.retry-btn').trigger('click')
    expect(refreshSpy).toHaveBeenCalledWith(true)
  })

  it('displays empty state when there are 0 pending messages', () => {
    const store = useMessagesStore()
    store.loading = false
    store.error = null
    store.pendingMessages = []

    const wrapper = mount(PendingView)

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.find('.empty-title').text()).toBe('공유 대기 브리핑이 없습니다')
  })

  it('navigates to message detail page when a message card is selected', async () => {
    const store = useMessagesStore()
    store.loading = false
    store.error = null

    const mockMessage: ShareMessage = {
      id: 'smsg_custom_99',
      title: '상세 페이지 네비게이션 테스트',
      body: '브리핑 본문',
      source_name: 'Tech Portal',
      status: 'pending',
      kakao_shared: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    store.pendingMessages = [mockMessage]

    const wrapper = mount(PendingView)

    const card = wrapper.findComponent({ name: 'MessageCard' })
    expect(card.exists()).toBe(true)

    // Trigger select event from MessageCard
    await card.vm.$emit('select', mockMessage)

    expect(mockRouterPush).toHaveBeenCalledTimes(1)
    expect(mockRouterPush).toHaveBeenCalledWith({
      name: 'message-detail',
      params: { id: 'smsg_custom_99' }
    })
  })

  it('triggers refresh when clicking the refresh button in header', async () => {
    const store = useMessagesStore()
    const refreshSpy = vi.spyOn(store, 'fetchPending').mockResolvedValue()

    const wrapper = mount(PendingView)

    await wrapper.find('.refresh-action-btn').trigger('click')
    expect(refreshSpy).toHaveBeenCalledWith(true)
  })

  it('navigates to register api view when clicking the API 등록 button (wired to home view)', async () => {
    const wrapper = mount(PendingView)

    const registerBtn = wrapper.find('.register-api-btn')
    expect(registerBtn.exists()).toBe(true)
    expect(registerBtn.text()).toContain('API 등록')

    await registerBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/register-api')
  })

  it('handles fetch event from failed cards in Pending view', async () => {
    const store = useMessagesStore()
    const failedMsg: ShareMessage = {
      id: 'failed_msg_1',
      title: '실패한 엔드포인트 브리핑',
      body: '5회 시도 후 실패',
      endpoint_id: 'ep_123',
      status: 'failed',
      fetch_status: 'failed',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    store.pendingMessages = [failedMsg]

    const wrapper = mount(PendingView)
    const card = wrapper.findComponent({ name: 'MessageCard' })
    expect(card.exists()).toBe(true)

    // Trigger fetch from the card
    await card.vm.$emit('fetch', failedMsg)
    // Verify component handles it without error
    expect(wrapper.exists()).toBe(true)
  })
})
