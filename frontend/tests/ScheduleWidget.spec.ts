import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ScheduleWidget from '@/components/ScheduleWidget.vue'
import { useThemeStore } from '@/stores/theme'

describe('ScheduleWidget Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders time-only selection heading and 5-attempt retry pipeline', () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        endpointName: 'Test Endpoint',
        enabled: true
      }
    })

    expect(wrapper.text()).toContain('수집 시각 선택 (What time)')
    expect(wrapper.text()).toContain('매일 자동으로 API 데이터를 가져올 시각을 선택하세요')

    // 5 attempts pipeline nodes
    const nodes = wrapper.findAll('.pipeline-node')
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

  it('updates time when steppers or period buttons are clicked', async () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        enabled: true
      }
    })

    // Stepper hour increment (09 -> 10)
    const stepperBtns = wrapper.findAll('.stepper-btn')
    // First stepper-btn is hour increment ▲
    await stepperBtns[0].trigger('click')

    expect(wrapper.emitted('update:scheduledTime')).toBeTruthy()
    expect(wrapper.emitted('update:scheduledTime')![0]).toEqual(['10:00'])

    // Click AM/PM period toggle button (09:00 AM -> 21:00 PM)
    const periodBtn = wrapper.find('.period-badge-btn')
    await periodBtn.trigger('click')

    const emitted = wrapper.emitted('update:scheduledTime')!
    expect(emitted[emitted.length - 1]).toEqual(['21:00'])
  })

  it('allows clicking an hour slot in the 24-hour visual ruler', async () => {
    const wrapper = mount(ScheduleWidget, {
      props: {
        scheduledTime: '09:00',
        enabled: true
      }
    })

    const slots = wrapper.findAll('.ruler-slot-btn')
    expect(slots.length).toBe(24)

    // Click 14:00 slot (index 14)
    await slots[14].trigger('click')

    expect(wrapper.emitted('update:scheduledTime')).toBeTruthy()
    expect(wrapper.emitted('update:scheduledTime')![0]).toEqual(['14:00'])
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
