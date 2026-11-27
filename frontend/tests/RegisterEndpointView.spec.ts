import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, config } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import RegisteredEndpointsView from '@/views/RegisteredEndpointsView.vue'
import RegisterEndpointView from '@/views/RegisterEndpointView.vue'
import { useEndpointsStore, DEFAULT_ENGLISH_SCRAPPER_URL } from '@/stores/endpoints'
import { useMessagesStore } from '@/stores/messages'
import { api } from '@/services/api'

const mockSchedule = vi.hoisted(() => ({ save: vi.fn(), read: vi.fn() }))
vi.mock('@/services/api', async (original) => {
  const actual = await original<typeof import('@/services/api')>()
  return { ...actual, englishScraperApi: { ...actual.englishScraperApi,
    saveSchedule: mockSchedule.save, schedule: mockSchedule.read } }
})
const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush
  })
}))

config.global.stubs.RouterLink = { props: ['to'], template: '<a :href="to"><slot /></a>' }

describe('RegisterEndpointView Component', () => {
  afterEach(() => vi.useRealTimers())
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouterPush.mockReset()
    mockSchedule.save.mockReset().mockImplementation(async value => ({...value, next_scheduled_at: '2026-11-18T00:00:00Z'}))
    mockSchedule.read.mockReset().mockResolvedValue({enabled:true, hour:6, minute:0, timezone:'Asia/Seoul', weekdays:[0,1,2,3,4], next_scheduled_at:'2026-11-17T21:00:00Z'})
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
    expect(wrapper.find('#english-scrape-time-value').exists()).toBe(true)
    expect(wrapper.text()).toContain('Moatok에서 저장한 시각')
    expect(wrapper.find('.retry-policy-box').exists()).toBe(false)
  })

  it('fills the Chosun Daily list preset with GET and generic JSON', async () => {
    const wrapper = mount(RegisterEndpointView)
    await wrapper.get('#endpoint-url').trigger('keydown', { key: 'ArrowDown', altKey: true })
    const button = wrapper.get('[role="menuitem"]')
    await button.trigger('click')
    expect((wrapper.find('#endpoint-url').element as HTMLInputElement).value)
      .toBe('https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10')
    await wrapper.find('form').trigger('submit.prevent')
    const endpoint = useEndpointsStore().endpoints.find(e => e.name === 'Chosun Daily Articles')
    expect(endpoint).toMatchObject({ method: 'GET', sourceType: 'generic_api', schedule: { enabled: false } })
  })

  it('provides testing endpoint preset with english_scrapper url', async () => {
    const wrapper = mount(RegisterEndpointView)
    await wrapper.get('#endpoint-url').trigger('keydown', { key: 'ArrowDown', altKey: true })
    const presetBtn = wrapper.findAll('[role="menuitem"]')[1]
    expect(presetBtn.exists()).toBe(true)
    expect(presetBtn.text()).toContain('English Scraper API')

    await presetBtn.trigger('click')

    const urlInput = wrapper.find('#endpoint-url').element as HTMLInputElement
    expect(urlInput.value).toBe(DEFAULT_ENGLISH_SCRAPPER_URL + '/api/v1/lessons/fetch')
    expect(urlInput.value).toContain('english-scrapper')
  })

  it('opens all three presets only after a continuous five-second hold', async () => {
    vi.useFakeTimers()
    const wrapper = mount(RegisterEndpointView)
    const input = wrapper.get('#endpoint-url')
    expect(wrapper.find('.test-preset-box').exists()).toBe(false)
    await input.trigger('pointerdown', { button: 0, isPrimary: true, clientX: 20, clientY: 20 })
    await vi.advanceTimersByTimeAsync(4999)
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    expect(wrapper.findAll('[role="menuitem"]')).toHaveLength(3)
    await wrapper.findAll('[role="menuitem"]')[2].trigger('click')
    expect((input.element as HTMLInputElement).value).toContain('japanese-scraper')
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('reopens the menu with a five-second mobile hold on an already-filled URL', async () => {
    vi.useFakeTimers()
    const wrapper = mount(RegisterEndpointView, { attachTo: document.body })
    const input = wrapper.get('#endpoint-url')
    await input.trigger('keydown', { key: 'ArrowDown', altKey: true })
    await wrapper.findAll('[role="menuitem"]')[0].trigger('click')
    const originalUrl = (input.element as HTMLInputElement).value
    expect(originalUrl).toContain('chosun-daily-api')
    await input.trigger('touchstart', { touches: [{ clientX: 20, clientY: 20 }] })
    // Native pointer cancellation must not cancel the separate touch timer.
    await input.trigger('pointercancel', { pointerType: 'touch' })
    await vi.advanceTimersByTimeAsync(4999)
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    expect(wrapper.findAll('[role="menuitem"]')).toHaveLength(3)
    await input.trigger('touchend', { touches: [] })
    expect(wrapper.find('[role="menu"]').exists()).toBe(true)
    expect((input.element as HTMLInputElement).value).toBe(originalUrl)
    await wrapper.findAll('[role="menuitem"]')[1].trigger('click')
    expect((input.element as HTMLInputElement).value).toContain('english-scrapper')
    await input.trigger('touchstart', { touches: [{ clientX: 20, clientY: 20 }] })
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="menu"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('cancels a short tap or scrolling gesture and dismisses the menu with Escape', async () => {
    vi.useFakeTimers()
    const wrapper = mount(RegisterEndpointView)
    const input = wrapper.get('#endpoint-url')
    await input.trigger('pointerdown', { button: 0, isPrimary: true, clientX: 0, clientY: 0 })
    await vi.advanceTimersByTimeAsync(2000)
    await input.trigger('pointerup')
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    await input.trigger('pointerdown', { button: 0, isPrimary: true, clientX: 0, clientY: 0 })
    await input.trigger('pointermove', { clientX: 0, clientY: 30 })
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    await input.trigger('keydown', { key: 'ArrowDown', altKey: true })
    await wrapper.get('[role="menu"]').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('links to the registered list and navigates back to Pending', async () => {
    const wrapper = mount(RegisterEndpointView)

    const backBtn = wrapper.find('.back-link')
    expect(backBtn.exists()).toBe(true)

    await backBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/')

    await wrapper.get('.bottom-home-btn').trigger('click')
    expect(mockRouterPush).toHaveBeenCalledTimes(2)
    expect(wrapper.get('a[href="/registed_api"]').text()).toBe('등록된 API 목록')
    expect(wrapper.find('.endpoint-items-list').exists()).toBe(false)
  })

  it('allows registering a new API endpoint with schedule and 5-attempt retry policy', async () => {
    const wrapper = mount(RegisterEndpointView)
    const endpointsStore = useEndpointsStore()

    // Fill fields
    await wrapper.find('#source-type').setValue('generic_api')
    await wrapper.find('#endpoint-url').setValue('https://api.testservice.com/feed')
    await wrapper.find('#endpoint-name').setValue('Test Feed Service')
    await wrapper.findAll('.preset-card-btn')[0].trigger('click')

    // Submit form
    await wrapper.find('.endpoint-form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.find('.success-alert').exists()).toBe(true)
    const added = endpointsStore.endpoints.find((e) => e.url === 'https://api.testservice.com/feed')
    expect(added).toBeDefined()
    expect(added?.name).toBe('Test Feed Service')
    expect(added?.schedule.enabled).toBe(true)
    expect(added?.schedule.scheduledTime).toBe('07:00')
    expect(added?.schedule.maxRetries).toBe(5)
    expect(added?.schedule.retryIntervalHours).toBe(1)
  })

  it('displays error if endpoint URL is invalid or empty', async () => {
    const wrapper = mount(RegisterEndpointView)

    await wrapper.find('#endpoint-url').setValue('')
    await wrapper.find('.endpoint-form').trigger('submit.prevent')

    expect(wrapper.find('.error-alert').exists()).toBe(true)
  })

  it('disables Fetch until the endpoint finishes saving its briefing', async () => {
    const endpointsStore = useEndpointsStore()
    const endpoint = endpointsStore.addEndpoint({ name: 'Weather', url: 'https://weather.test/alerts' })
    let finishSaving!: () => void
    const saving = new Promise<void>(resolve => { finishSaving = resolve })
    const save = vi.spyOn(api, 'saveFetchedMessage').mockImplementation(async message => {
      await saving
      return { message }
    })
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ title: 'Weather alert' }))
    )
    const wrapper = mount(RegisteredEndpointsView)
    try {
      const button = wrapper.get<HTMLButtonElement>('button.btn-fetch')
      expect(button.element.disabled).toBe(false)
      await button.trigger('click')
      await flushPromises()
      expect(save).toHaveBeenCalledOnce()
      expect(button.element.disabled).toBe(true)
      expect(wrapper.get('.status-fetching').text()).toBe('수집 중')
      await button.trigger('click')
      expect(await endpointsStore.triggerFetch(endpoint.id, true)).toMatchObject({ success: false })
      expect(fetch).toHaveBeenCalledOnce()

      finishSaving()
      await flushPromises()
      expect(button.element.disabled).toBe(false)
      expect(wrapper.get('.status-success').text()).toBe('수집 정상')
    } finally {
      finishSaving()
      await flushPromises()
      wrapper.unmount()
      fetch.mockRestore()
      save.mockRestore()
    }
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

    const wrapper = mount(RegisteredEndpointsView)

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


describe('Moatok server schedule bridge', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    mockSchedule.save.mockReset().mockImplementation(async value => ({...value, next_scheduled_at:'2026-11-18T00:00:00Z'}))
    mockSchedule.read.mockReset().mockResolvedValue({enabled:true,hour:6,minute:0,timezone:'Asia/Seoul',weekdays:[0,1,2,3,4],next_scheduled_at:'2026-11-17T21:00:00Z'})
  })
  it('sends the time selected in Moatok before reporting successful registration', async () => {
    const wrapper = mount(RegisterEndpointView)
    await wrapper.get('#endpoint-url').setValue(DEFAULT_ENGLISH_SCRAPPER_URL+'/api/v1/lessons/fetch')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(mockSchedule.save).toHaveBeenCalledWith({enabled:true,hour:9,minute:0,timezone:'Asia/Seoul',weekdays:[0,1,2,3,4]})
    expect(wrapper.find('.success-alert').exists()).toBe(true)
    wrapper.unmount()
  })
  it('does not register an endpoint or claim success when server scheduling fails', async () => {
    mockSchedule.save.mockRejectedValue(new Error('Schedule server unavailable'))
    const wrapper = mount(RegisterEndpointView)
    const originalCount = useEndpointsStore().endpoints.length
    await wrapper.get('#endpoint-url').setValue(DEFAULT_ENGLISH_SCRAPPER_URL+'/api/v1/lessons/fetch')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.get('.error-alert').text()).toContain('Schedule server unavailable')
    expect(wrapper.find('.success-alert').exists()).toBe(false)
    expect(useEndpointsStore().endpoints).toHaveLength(originalCount)
    wrapper.unmount()
  })
  it('loads the persisted schedule, then sends disabled state from Moatok', async () => {
    const wrapper = mount(RegisteredEndpointsView)
    const edit = wrapper.findAll('button').find(button=>button.text()==='서버 수집 예약 변경')!
    await edit.trigger('click')
    await flushPromises()
    expect(mockSchedule.read).toHaveBeenCalledOnce()
    expect(wrapper.get('#english-scrape-time-value').text()).toBe('06:00')
    await wrapper.get('.switch-input').setValue(false)
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(mockSchedule.save).toHaveBeenCalledWith(expect.objectContaining({enabled:false,hour:6,minute:0}))
    expect(useEndpointsStore().endpoints[0].schedule.enabled).toBe(false)
    expect(wrapper.get('.notif-feedback-box').text()).toContain('서버에 저장')
    wrapper.unmount()
  })
})
