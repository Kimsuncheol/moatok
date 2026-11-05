import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PendingView from '@/views/PendingView.vue'
import { useMessagesStore } from '@/stores/messages'
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
    mockRouterPush.mockReset()
    vi.restoreAllMocks()
    vi.spyOn(api, 'getPendingMessages').mockResolvedValue({
      messages: [],
      count: 0
    })
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
})
