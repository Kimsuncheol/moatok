import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import OpenChatSchedule from '../src/components/OpenChatSchedule.vue'

describe('Open Chat schedule export', () => {
  it('rejects past dates without creating a download', async () => {
    const wrapper = mount(OpenChatSchedule)
    await wrapper.find('input').setValue('Room')
    await wrapper.find('textarea').setValue('Hello')
    await wrapper.find('input[type="datetime-local"]').setValue('2000-01-01T09:00')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.find('[role="status"]').text()).toContain('미래')
  })
  it('exports an immutable ID, exact room and timezone-aware date and clears the draft', async () => {
    const create = vi.fn(() => 'blob:test')
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: create, revokeObjectURL: vi.fn() }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const wrapper = mount(OpenChatSchedule)
    await wrapper.find('input').setValue('Room')
    await wrapper.find('textarea').setValue('Hello')
    await wrapper.find('input[type="datetime-local"]').setValue('2099-01-01T09:00')
    await wrapper.find('form').trigger('submit')
    expect(create).toHaveBeenCalledOnce()
    expect(wrapper.find('textarea').element.value).toBe('')
    expect(wrapper.find('[role="status"]').text()).toContain('가져와야')
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })
})
