import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AppearanceToggle from '@/components/AppearanceToggle.vue'
import { useThemeStore } from '@/stores/theme'

describe('AppearanceToggle Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders a segmented control without any dropdown (<select>) element', () => {
    const wrapper = mount(AppearanceToggle)

    // Critical constraint: MUST NOT use a dropdown
    expect(wrapper.find('select').exists()).toBe(false)
    expect(wrapper.find('.appearance-segmented-control').exists()).toBe(true)

    // Must have 3 options: System, Light, Dark
    const buttons = wrapper.findAll('.segment-btn')
    expect(buttons).toHaveLength(3)

    const labels = buttons.map((b) => b.text())
    expect(labels.some((l) => l.includes('시스템'))).toBe(true)
    expect(labels.some((l) => l.includes('라이트'))).toBe(true)
    expect(labels.some((l) => l.includes('다크'))).toBe(true)
  })

  it('switches appearance mode when segment buttons are clicked', async () => {
    const wrapper = mount(AppearanceToggle)
    const themeStore = useThemeStore()

    const buttons = wrapper.findAll('.segment-btn')
    const lightBtn = buttons.find((b) => b.text().includes('라이트'))
    const darkBtn = buttons.find((b) => b.text().includes('다크'))
    const systemBtn = buttons.find((b) => b.text().includes('시스템'))

    await darkBtn?.trigger('click')
    expect(themeStore.mode).toBe('dark')
    expect(darkBtn?.classes()).toContain('active')

    await lightBtn?.trigger('click')
    expect(themeStore.mode).toBe('light')
    expect(lightBtn?.classes()).toContain('active')

    await systemBtn?.trigger('click')
    expect(themeStore.mode).toBe('system')
    expect(systemBtn?.classes()).toContain('active')
  })
})
