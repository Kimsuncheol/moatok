import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const mockNeedRefresh = ref(false)
const mockOfflineReady = ref(false)
const mockUpdateServiceWorker = vi.fn()

vi.mock('virtual:pwa-register/vue', () => ({
  useRegisterSW: () => ({
    needRefresh: mockNeedRefresh,
    offlineReady: mockOfflineReady,
    updateServiceWorker: mockUpdateServiceWorker
  })
}))

import ReloadPrompt from '@/components/ReloadPrompt.vue'

describe('ReloadPrompt Component (PWA Update Prompt)', () => {
  beforeEach(() => {
    mockNeedRefresh.value = false
    mockOfflineReady.value = false
    mockUpdateServiceWorker.mockReset()
  })

  it('remains hidden when no update is pending', () => {
    const wrapper = mount(ReloadPrompt)
    expect(wrapper.find('.reload-prompt').exists()).toBe(false)
  })

  it('displays the update prompt when a new version is available', async () => {
    mockNeedRefresh.value = true
    const wrapper = mount(ReloadPrompt)

    const prompt = wrapper.find('.reload-prompt')
    expect(prompt.exists()).toBe(true)
    expect(prompt.text()).toContain('새 버전 사용 가능')
    expect(wrapper.find('.btn-update').exists()).toBe(true)
  })

  it('triggers updateServiceWorker when user clicks update', async () => {
    mockNeedRefresh.value = true
    const wrapper = mount(ReloadPrompt)

    const updateBtn = wrapper.find('.btn-update')
    await updateBtn.trigger('click')

    expect(mockUpdateServiceWorker).toHaveBeenCalledWith(true)
  })

  it('dismisses the prompt when user clicks later', async () => {
    mockNeedRefresh.value = true
    const wrapper = mount(ReloadPrompt)

    const dismissBtn = wrapper.find('.btn-dismiss')
    await dismissBtn.trigger('click')

    expect(mockNeedRefresh.value).toBe(false)
  })
})
