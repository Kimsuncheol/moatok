import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import MyChatAutomation from '@/components/MyChatAutomation.vue'
import { myChatAutomationApi as api } from '@/services/api'
vi.mock('@/services/api', () => ({ myChatAutomationApi: { status: vi.fn(), get: vi.fn(), connect: vi.fn(), save: vi.fn(), disconnect: vi.fn() } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ userUid: null, isAuthenticated: false }) }))
beforeEach(() => { vi.resetAllMocks(); setActivePinia(createPinia()) })
describe('automatic sending availability', () => {
  it('disables connection and options when server configuration is missing', async () => {
    vi.mocked(api.status).mockResolvedValue({ configured: false })
    const wrapper = mount(MyChatAutomation)
    await flushPromises()
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('서버 설정이 완료되지 않았습니다')
    expect(api.get).not.toHaveBeenCalled()
    expect(api.connect).not.toHaveBeenCalled()
  })
  it('enables controls only for a configured, connected account', async () => {
    vi.mocked(api.status).mockResolvedValue({ configured: true })
    vi.mocked(api.get).mockResolvedValue({ connected: true, on_new: false, daily: false, daily_time: '09:00', error: '' })
    const wrapper = mount(MyChatAutomation)
    await flushPromises()
    expect(wrapper.get('fieldset').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('자동 전송 연결 해제')
  })
  it('keeps connection disabled when the status request fails', async () => {
    vi.mocked(api.status).mockRejectedValue(new Error('Network unavailable'))
    const wrapper = mount(MyChatAutomation)
    await flushPromises()
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Network unavailable')
  })
})

it('applies a selected time only after pressing 설정', async () => {
  vi.mocked(api.status).mockResolvedValue({ configured: true })
  vi.mocked(api.get).mockResolvedValue({ connected: true, on_new: false, daily: false, daily_time: '09:00', error: '' })
  const wrapper = mount(MyChatAutomation)
  await flushPromises()
  await wrapper.get('.automation-time-trigger').trigger('click')
  const selects = wrapper.findAll('select')
  await selects[0].setValue('18')
  await selects[1].setValue('30')
  expect(wrapper.get('#automation-time-value').text()).toBe('09:00')
  await wrapper.get('.automation-time-actions button:last-child').trigger('click')
  expect(wrapper.get('#automation-time-value').text()).toBe('18:30')
  expect(api.save).not.toHaveBeenCalled()
})
