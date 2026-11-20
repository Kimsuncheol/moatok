import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { RouterView } from 'vue-router'
import { afterEach, expect, it, vi } from 'vitest'
import BottomNav from '@/components/BottomNav.vue'
import router from '@/router'
import { englishScraperApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useEndpointsStore } from '@/stores/endpoints'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

it('opens the same saved list from Settings and registration, including after deleting the last endpoint', async () => {
  localStorage.clear()
  await router.push('/settings')
  const pinia = createPinia()
  const wrapper = mount({ components: { RouterView, BottomNav }, template: '<RouterView /><BottomNav />' }, {
    global: { plugins: [pinia, router], stubs: { AccountSettings: true } }
  })
  async function follow(href: string) {
    await wrapper.get(`a[href="${href}"]`).trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe(href))
    await flushPromises()
  }

  await follow('/registed_api')
  expect(wrapper.get('.nav-tab.active').text()).toBe('Settings')
  expect(wrapper.get('.item-name').text()).toBe('English Scraper API')
  expect(wrapper.get('.settings-back-link').attributes('href')).toBe('/settings')
  await follow('/register-api')
  await wrapper.get('#source-type').setValue('generic_api')
  await wrapper.get('#endpoint-name').setValue('Daily feed')
  await wrapper.get('#endpoint-url').setValue('https://example.org/feed')
  await wrapper.get('.endpoint-form').trigger('submit')
  await follow('/registed_api')
  const feed = wrapper.findAll('.endpoint-item').find(item => item.text().includes('Daily feed'))!
  const store = useEndpointsStore(pinia)
  const id = store.endpoints.find(endpoint => endpoint.name === 'Daily feed')!.id
  const fetch = vi.spyOn(store, 'triggerFetch').mockResolvedValue({ success: true, message: '1개' })
  await feed.get('.btn-fetch').trigger('click')
  expect(fetch).toHaveBeenCalledWith(id, true)
  expect(wrapper.get('[role="status"]').text()).toContain('1개')

  vi.spyOn(window, 'confirm').mockReturnValue(true)
  await feed.get('.btn-delete').trigger('click')
  await wrapper.get('.btn-delete').trigger('click')
  await follow('/settings')
  await follow('/registed_api')
  expect(wrapper.get('.empty-endpoints-box').isVisible()).toBe(true)
  expect(wrapper.get('a[href="/register-api"]').isVisible()).toBe(true)
  wrapper.unmount()
})

it('shows all registered schedules and filters the table by API name', async () => {
  await router.push('/registed_api')
  const pinia = createPinia()
  const store = useEndpointsStore(pinia)
  store.addEndpoint({ name: 'Daily feed', url: 'https://example.org/feed', schedule: { scheduledTime: '18:30' } })
  store.addEndpoint({ name: 'Paused feed', url: 'https://example.org/paused', schedule: { enabled: false } })

  const checkSchedule = vi.spyOn(englishScraperApi, 'schedule').mockResolvedValue({
    enabled: true, hour: 7, minute: 15, weekdays: [0, 4], timezone: 'Asia/Seoul',
    next_scheduled_at: '2026-11-23T07:15:00+09:00'
  })
  const auth = useAuthStore(pinia)
  const wrapper = mount({ components: { RouterView, BottomNav }, template: '<RouterView /><BottomNav />' }, {
    global: { plugins: [pinia, router] }
  })

  await wrapper.get('a[href="/settings/api-schedules"]').trigger('click')
  await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('api-schedules'))
  await flushPromises()

  expect(wrapper.get('.settings-back-link').attributes('href')).toBe('/registed_api')
  expect(wrapper.get('.nav-tab.active').text()).toBe('Settings')
  const chips = wrapper.findAll('.api-schedule-filters button')
  const table = wrapper.get('table')
  expect(chips.map(chip => chip.text())).toEqual(['전체', 'Paused feed', 'Daily feed', 'English Scraper API'])
  expect(chips[0].attributes('aria-pressed')).toBe('true')
  expect(table.findAll('tbody tr')).toHaveLength(3)
  expect(table.text()).toContain('매일 18:30')
  expect(table.text()).toContain('비활성')
  expect(table.text()).toContain('확인 중')
  expect(checkSchedule).not.toHaveBeenCalled()

  auth.$patch({ loading: false, status: 'authenticated', profile: { uid: 'admin', email: null, role: 'admin' } })
  await flushPromises()
  expect(checkSchedule).toHaveBeenCalledTimes(1)
  expect(table.text()).toContain('월 · 금 07:15')
  expect(table.text()).toContain('Asia/Seoul')
  expect(table.find('time[datetime="2026-11-23T07:15:00+09:00"]').exists()).toBe(true)

  await chips[2].trigger('click')
  expect(chips[2].attributes('aria-pressed')).toBe('true')
  expect(chips[0].attributes('aria-pressed')).toBe('false')
  expect(table.findAll('tbody th').map(row => row.text())).toEqual(['Daily feed'])

  await chips[0].trigger('click')
  expect(table.findAll('tbody tr')).toHaveLength(3)
  expect(checkSchedule).toHaveBeenCalledTimes(1)
  wrapper.unmount()
})
