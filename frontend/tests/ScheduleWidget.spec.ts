import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScheduleWidget from '@/components/ScheduleWidget.vue'

describe('ScheduleWidget Component', () => {
  it('renders Schedule-X widget title and 5-attempt retry timeline', () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    expect(wrapper.text()).toContain('Schedule-X 일정 시각화')
    expect(wrapper.text()).toContain('Schedule-X v4')
    expect(wrapper.text()).toContain('기준 시각: 09:00')

    // 5 attempts timeline nodes
    const nodes = wrapper.findAll('.timeline-node')
    expect(nodes.length).toBe(5)

    // Check step 1: 09:00
    expect(nodes[0].text()).toContain('09:00')
    expect(nodes[0].text()).toContain('1차 자동 수집')

    // Check step 2: 10:00 (+1h)
    expect(nodes[1].text()).toContain('10:00')
    expect(nodes[1].text()).toContain('2차 재시도 (+1h)')

    // Check step 5: 13:00 (+4h)
    expect(nodes[4].text()).toContain('13:00')
    expect(nodes[4].text()).toContain('5차 최종 재시도 (+4h)')
    expect(nodes[4].text()).toContain('실패 시 Pending 뷰에 Fetch 버튼 제공')
  })

  it('updates timeline when scheduledTime prop changes', async () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '14:30',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    const nodes = wrapper.findAll('.timeline-node')
    expect(nodes[0].text()).toContain('14:30')
    expect(nodes[1].text()).toContain('15:30')
    expect(nodes[4].text()).toContain('18:30')

    await wrapper.setProps({ scheduledTime: '22:15' })
    const updatedNodes = wrapper.findAll('.timeline-node')
    expect(updatedNodes[0].text()).toContain('22:15')
    expect(updatedNodes[1].text()).toContain('23:15')
    // Next day wrap around
    expect(updatedNodes[2].text()).toContain('00:15')
  })

  it('emits update:scheduledTime when quick preset button is clicked', async () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    const presets = wrapper.findAll('.preset-chip')
    expect(presets.length).toBeGreaterThanOrEqual(4)

    // Click 18:00 preset
    const eveningPreset = presets.find(p => p.text().includes('18:00'))
    expect(eveningPreset).toBeDefined()
    await eveningPreset?.trigger('click')

    expect(wrapper.emitted('update:scheduledTime')).toBeTruthy()
    expect(wrapper.emitted('update:scheduledTime')![0]).toEqual(['18:00'])
  })

  it('applies disabled state styling when enabled prop is false', () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: false
      }
    })

    expect(wrapper.classes()).toContain('is-disabled')
  })
})
