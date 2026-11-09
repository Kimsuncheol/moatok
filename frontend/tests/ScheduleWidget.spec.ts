import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ScheduleWidget from '@/components/ScheduleWidget.vue'
import { useThemeStore } from '@/stores/theme'

describe('ScheduleWidget Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders retry timeline without the horizontal timeline', () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    expect(wrapper.text()).toContain('수집 시각 선택 (What time)')
    expect(wrapper.text()).toContain('매일 자동으로 API 데이터를 가져올 시각을 선택하세요')

    expect(wrapper.findAll('.pipeline-node')).toHaveLength(5)
    expect(wrapper.find('.ruler-section').exists()).toBe(false)
    expect(wrapper.find('.fetch-time-summary').exists()).toBe(true)
  })

  it('dynamically adapts styling to current appearance mode (light / dark)', async () => {
    const themeStore = useThemeStore()

    // Test Light Mode
    themeStore.setMode('light')
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        enabled: true
      }
    })

    expect(wrapper.classes()).toContain('theme-light')
    expect(wrapper.text()).toContain('라이트 모드')

    // Switch to Dark Mode
    themeStore.setMode('dark')
    await wrapper.vm.$nextTick()

    expect(wrapper.classes()).toContain('theme-dark')
    expect(wrapper.text()).toContain('다크 모드')
  })

  it('shows the fetch time from the selected preset without a separate picker', async () => {
    const wrapper = mount(ScheduleWidget, { props: { scheduledTime: '09:00', enabled: true } })
    expect(wrapper.find('.automation-time-trigger').exists()).toBe(false)
    expect(wrapper.get('.fetch-time-summary').text()).toContain('09:00')
    await wrapper.setProps({ scheduledTime: '12:30' })
    expect(wrapper.get('.fetch-time-summary').text()).toContain('12:30')
  })

  it('emits update:scheduledTime when quick preset button is clicked', async () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    const presets = wrapper.findAll('.preset-card-btn')
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
