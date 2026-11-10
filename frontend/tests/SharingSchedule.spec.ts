import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import SharingSchedule from '@/components/SharingSchedule.vue'
import { useSharingScheduleStore } from '@/stores/sharingSchedule'
import type { ShareMessage } from '@/types'
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ userUid: 'user', isAuthenticated: true }) }))
vi.mock('@/services/api', () => ({ myChatAutomationApi: { get: vi.fn(() => new Promise(() => {})) } }))
const message: ShareMessage = { id: 'server-message', title: 'Title', body: 'Body', status: 'pending', created_at: '', updated_at: '' }
beforeEach(() => setActivePinia(createPinia()))
function ready() {
  const store = useSharingScheduleStore()
  vi.spyOn(store, 'refresh').mockResolvedValue(undefined)
  store.loading = false
  store.settings = { connected: true, on_new: false, daily: true, daily_time: '18:30', error: '' }
  return store
}
describe('Pending sending schedule', () => {
  it('shows the saved daily time with its timezone', () => {
    ready()
    const wrapper = mount(SharingSchedule, { props: { message } })
    expect(wrapper.text()).toContain('매일 18:30')
    expect(wrapper.text()).toContain('한국 시간')
    expect(wrapper.text()).toContain('최신 5개 모음')
  })
  it('shows new-content timing alongside the daily schedule', () => {
    const store = ready()
    store.settings!.on_new = true
    const wrapper = mount(SharingSchedule, { props: { message } })
    expect(wrapper.text()).toContain('수집 후 약 5분 이내')
    expect(wrapper.text()).toContain('18:30')
  })
  it('does not promise an automatic send for browser-only cards', () => {
    ready()
    const wrapper = mount(SharingSchedule, { props: { message: { ...message, id: 'local_article', endpoint_id: 'endpoint' } } })
    expect(wrapper.text()).toContain('자동 전송 예약 없음')
    expect(wrapper.text()).not.toContain('18:30')
  })
  it('distinguishes disabled sending from an unavailable schedule', async () => {
    const store = ready()
    store.settings!.daily = false
    const wrapper = mount(SharingSchedule, { props: { message } })
    expect(wrapper.text()).toContain('자동 전송 예약 없음')
    store.unavailable = true
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('확인하지 못했습니다')
  })
  it('hides sending schedules for completed messages', () => {
    ready()
    const wrapper = mount(SharingSchedule, { props: { message: { ...message, status: 'shared', kakao_shared: true } } })
    expect(wrapper.find('.sharing-schedule').exists()).toBe(false)
  })
})
