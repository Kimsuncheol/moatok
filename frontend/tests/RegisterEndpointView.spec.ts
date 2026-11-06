import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import RegisterEndpointView from '@/views/RegisterEndpointView.vue'
import { useEndpointsStore, DEFAULT_ENGLISH_SCRAPPER_URL } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush
  })
}))

describe('RegisterEndpointView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouterPush.mockReset()
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear()
    }
  })

  it('renders title, input fields for API endpoints, and schedule configuration', () => {
    const wrapper = mount(RegisterEndpointView)

    // Check title
    expect(wrapper.find('.view-title').text()).toBe('Register an API endpoint')

    // Check input fields
    expect(wrapper.find('#endpoint-url').exists()).toBe(true)
    expect(wrapper.find('#endpoint-name').exists()).toBe(true)
    expect(wrapper.find('.method-selector').exists()).toBe(true)

    // Check schedule inputs & retry policy
    expect(wrapper.find('.schedule-title').text()).toContain('스케줄 및 자동 수집')
    expect(wrapper.find('#schedule-time').exists()).toBe(true)
    expect(wrapper.find('.retry-policy-box').text()).toContain('최대 5회')
    expect(wrapper.find('.retry-policy-box').text()).toContain('1시간 후')
  })

  it('provides testing endpoint preset with english_scrapper url', async () => {
    const wrapper = mount(RegisterEndpointView)

    const presetBtn = wrapper.find('.preset-fill-btn')
    expect(presetBtn.exists()).toBe(true)
    expect(presetBtn.text()).toContain('테스트 엔드포인트 채우기')

    await presetBtn.trigger('click')

    const urlInput = wrapper.find('#endpoint-url').element as HTMLInputElement
    expect(urlInput.value).toBe(DEFAULT_ENGLISH_SCRAPPER_URL + '/api/v1/lessons/fetch')
    expect(urlInput.value).toContain('english-scrapper')
  })

  it('navigates back to home view when clicking home navigation links', async () => {
    const wrapper = mount(RegisterEndpointView)

    const backBtn = wrapper.find('.back-link')
    expect(backBtn.exists()).toBe(true)

    await backBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/')

    const bottomHomeBtn = wrapper.find('.bottom-home-btn')
    await bottomHomeBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/')
  })

  it('allows registering a new API endpoint with schedule and 5-attempt retry policy', async () => {
    const wrapper = mount(RegisterEndpointView)
    const endpointsStore = useEndpointsStore()

    // Fill fields
    await wrapper.find('#endpoint-url').setValue('https://api.testservice.com/feed')
    await wrapper.find('#endpoint-name').setValue('Test Feed Service')
    await wrapper.find('#schedule-time').setValue('08:30')

    // Submit form
    await wrapper.find('.endpoint-form').trigger('submit.prevent')

    expect(wrapper.find('.success-alert').exists()).toBe(true)
    const added = endpointsStore.endpoints.find((e) => e.url === 'https://api.testservice.com/feed')
    expect(added).toBeDefined()
    expect(added?.name).toBe('Test Feed Service')
    expect(added?.schedule.enabled).toBe(true)
    expect(added?.schedule.scheduledTime).toBe('08:30')
    expect(added?.schedule.maxRetries).toBe(5)
    expect(added?.schedule.retryIntervalHours).toBe(1)
  })

  it('displays error if endpoint URL is invalid or empty', async () => {
    const wrapper = mount(RegisterEndpointView)

    await wrapper.find('#endpoint-url').setValue('')
    await wrapper.find('.endpoint-form').trigger('submit.prevent')

    expect(wrapper.find('.error-alert').exists()).toBe(true)
  })

  it('simulates 5 failed attempts and generates card in Pending view with Fetch button', async () => {
    const endpointsStore = useEndpointsStore()
    const messagesStore = useMessagesStore()

    // Seed an endpoint
    const ep = endpointsStore.addEndpoint({
      name: 'Weather Alert API',
      url: 'https://weather.test/alerts',
      schedule: { maxRetries: 5, retryIntervalHours: 1 }
    })

    const wrapper = mount(RegisterEndpointView)

    // Click simulate fail button
    const simulateBtn = wrapper.find('.btn-simulate-fail')
    expect(simulateBtn.exists()).toBe(true)
    await simulateBtn.trigger('click')

    // Expect message in messagesStore with status 'failed'
    const failedMsg = messagesStore.pendingMessages.find((m) => m.endpoint_id === ep.id)
    expect(failedMsg).toBeDefined()
    expect(failedMsg?.status).toBe('failed')
    expect(failedMsg?.fetch_attempts).toBe(5)
    expect(failedMsg?.body).toContain('Fetch')
  })
})
