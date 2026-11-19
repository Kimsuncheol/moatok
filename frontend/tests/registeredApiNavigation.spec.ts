import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { RouterView } from 'vue-router'
import { afterEach, expect, it, vi } from 'vitest'
import BottomNav from '@/components/BottomNav.vue'
import router from '@/router'
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
