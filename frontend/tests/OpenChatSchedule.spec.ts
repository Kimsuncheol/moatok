import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import OpenChatSchedule from '../src/components/OpenChatSchedule.vue'

describe('Open Chat schedule export', () => {
  it('applies time changes and discards cancelled edits', async () => {
    const wrapper = mount(OpenChatSchedule)
    const trigger = wrapper.find('.automation-time-trigger')
    await trigger.trigger('click')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.findAll('select')[0].setValue('14')
    await wrapper.findAll('select')[1].setValue('35')
    await wrapper.findAll('.automation-time-actions button')[1].trigger('click')
    expect(trigger.text()).toBe('14:35')
    await trigger.trigger('click')
    await wrapper.findAll('select')[0].setValue('23')
    await wrapper.findAll('.automation-time-actions button')[0].trigger('click')
    expect(trigger.text()).toBe('14:35')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })
  it('rejects past dates without creating a download', async () => {
    const wrapper = mount(OpenChatSchedule)
    await wrapper.find('input').setValue('Room')
    await wrapper.find('textarea').setValue('Hello')
    await wrapper.find('input[type="date"]').setValue('2000-01-01')
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
    await wrapper.find('input[type="date"]').setValue('2099-01-01')
    await wrapper.find('form').trigger('submit')
    expect(create).toHaveBeenCalledOnce()
    expect(wrapper.find('textarea').element.value).toBe('')
    expect(wrapper.find('[role="status"]').text()).toContain('가져와야')
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })
})
