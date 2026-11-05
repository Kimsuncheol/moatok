import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import HistoryView from '@/views/HistoryView.vue'
import { useMessagesStore } from '@/stores/messages'
import type { ShareMessage } from '@/types'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush
  })
}))

describe('HistoryView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouterPush.mockReset()
    vi.restoreAllMocks()
  })

  const confirmedMessage: ShareMessage = {
    id: 'msg_confirmed_1',
    title: '클라우드 보안 및 최소 권한 가이드',
    body: '보안 가이드 요약 내용입니다.',
    source_name: '보안 뉴스',
    status: 'shared',
    kakao_shared: true,
    shared_by_user_at: '2026-11-06T00:30:00Z',
    shared_by_user_id: 'user_admin',
    last_share_channel: 'kakao_sdk',
    share_attempt_count: 1,
    last_share_attempt_at: '2026-11-06T00:28:00Z',
    last_share_attempt_channel: 'kakao_sdk',
    created_at: '2026-11-06T00:00:00Z',
    updated_at: '2026-11-06T00:30:00Z'
  }

  const startedMessage: ShareMessage = {
    id: 'msg_started_2',
    title: 'Vue 3 PWA 모바일 우선 아키텍처',
    body: 'PWA 아키텍처 브리핑 내용입니다.',
    source_name: '프론트엔드 허브',
    status: 'pending',
    kakao_shared: false,
    share_attempt_count: 2,
    last_share_attempt_at: '2026-11-06T00:45:00Z',
    last_share_attempt_channel: 'web_share',
    created_at: '2026-11-06T00:10:00Z',
    updated_at: '2026-11-06T00:45:00Z'
  }

  const unattemptedMessage: ShareMessage = {
    id: 'msg_pending_3',
    title: '아직 공유하지 않은 대기 기사',
    body: '대기 중인 내용입니다.',
    source_name: '신규 피드',
    status: 'pending',
    kakao_shared: false,
    share_attempt_count: 0,
    created_at: '2026-11-06T00:20:00Z',
    updated_at: '2026-11-06T00:20:00Z'
  }

  it('shows share attempts and confirmed results only when supported by reliable backend events', async () => {
    const messagesStore = useMessagesStore()
    // Populate store with confirmed, started, and unattempted messages
    messagesStore.historyMessages = [confirmedMessage, startedMessage, unattemptedMessage]
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue(messagesStore.historyMessages)

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    const cards = wrapper.findAll('.history-card')
    // Crucial requirement: unattemptedMessage (0 attempts, unshared) must be EXCLUDED
    expect(cards).toHaveLength(2)

    const cardTexts = cards.map((c) => c.text())
    expect(cardTexts.some((t) => t.includes('클라우드 보안 및 최소 권한 가이드'))).toBe(true)
    expect(cardTexts.some((t) => t.includes('Vue 3 PWA 모바일 우선 아키텍처'))).toBe(true)
    expect(cardTexts.some((t) => t.includes('아직 공유하지 않은 대기 기사'))).toBe(false)
  })

  it('clearly distinguishes "share started" from "share confirmed" with distinct badges and events', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.historyMessages = [confirmedMessage, startedMessage]
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue(messagesStore.historyMessages)

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    // 1. Confirmed message verification
    const confirmedCard = wrapper.findAll('.history-card')[0]
    expect(confirmedCard.find('.badge-confirmed').exists()).toBe(true)
    expect(confirmedCard.find('.badge-confirmed').text()).toContain('공유 완료 확정')
    expect(confirmedCard.find('.event-confirmed').exists()).toBe(true)
    expect(confirmedCard.find('.event-confirmed').text()).toContain('카카오톡 JS SDK')

    // 2. Started (in-progress) message verification
    const startedCard = wrapper.findAll('.history-card')[1]
    expect(startedCard.find('.badge-started').exists()).toBe(true)
    expect(startedCard.find('.badge-started').text()).toContain('공유 시작됨')
    expect(startedCard.find('.event-started').exists()).toBe(true)
    expect(startedCard.find('.event-started').text()).toContain('시도 횟수: 2회')
    expect(startedCard.find('.event-started').text()).toContain('시스템 공유 시트 (Web Share)')
    expect(startedCard.find('.confirm-action-btn').exists()).toBe(true)
  })

  it('does not imply that a specific Open Chat room received the message unless verified', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.historyMessages = [confirmedMessage]
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue(messagesStore.historyMessages)

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    const notice = wrapper.find('.openchat-verification-notice')
    expect(notice.exists()).toBe(true)
    expect(notice.text()).toContain('전송 대상 안내')
    expect(notice.text()).toContain('외부 웹 앱에는 개별 오픈채팅방의 수신 영수증이 제공되지 않습니다')
    // Must NOT claim unverified delivery to a specific open chat
    expect(wrapper.text()).not.toContain('오픈채팅방에 성공적으로 전달되었습니다')
  })

  it('allows filtering by all, confirmed, and started status', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.historyMessages = [confirmedMessage, startedMessage]
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue(messagesStore.historyMessages)

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    const chips = wrapper.findAll('.chip-btn')
    expect(chips).toHaveLength(3)

    // Filter to Confirmed only
    await chips[1].trigger('click')
    expect(wrapper.findAll('.history-card')).toHaveLength(1)
    expect(wrapper.find('.history-card').text()).toContain('클라우드 보안 및 최소 권한 가이드')

    // Filter to Started only
    await chips[2].trigger('click')
    expect(wrapper.findAll('.history-card')).toHaveLength(1)
    expect(wrapper.find('.history-card').text()).toContain('Vue 3 PWA 모바일 우선 아키텍처')

    // Filter to All
    await chips[0].trigger('click')
    expect(wrapper.findAll('.history-card')).toHaveLength(2)
  })

  it('allows user to confirm share completion for started messages', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.historyMessages = [startedMessage]
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue(messagesStore.historyMessages)
    const markSharedSpy = vi.spyOn(messagesStore, 'markAsShared').mockResolvedValue({
      ...startedMessage,
      status: 'shared',
      kakao_shared: true,
      shared_by_user_at: new Date().toISOString()
    })

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    const confirmBtn = wrapper.find('.confirm-action-btn')
    expect(confirmBtn.exists()).toBe(true)
    await confirmBtn.trigger('click')
    await flushPromises()

    expect(markSharedSpy).toHaveBeenCalledWith('msg_started_2', 'web_share')
    expect(wrapper.find('.feedback-banner').exists()).toBe(true)
  })

  it('renders clean empty state when no history messages exist', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.historyMessages = []
    vi.spyOn(messagesStore, 'fetchHistory').mockResolvedValue([])

    const wrapper = mount(HistoryView, {
      global: {
        stubs: {
          RouterLink: true
        }
      }
    })
    await flushPromises()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.find('.empty-title').text()).toContain('기록된 공유 이력이 없습니다')
  })
})
