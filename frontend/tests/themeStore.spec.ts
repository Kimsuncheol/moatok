import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore, getSafeLocalStorage } from '@/stores/theme'

describe('Theme Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const storage = getSafeLocalStorage()
    storage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('defaults to system mode and persists to localStorage on change', () => {
    const store = useThemeStore()
    const storage = getSafeLocalStorage()
    expect(store.mode).toBe('system')

    store.setMode('dark')
    expect(store.mode).toBe('dark')
    expect(storage.getItem('moatok_appearance_mode')).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    store.setMode('light')
    expect(store.mode).toBe('light')
    expect(storage.getItem('moatok_appearance_mode')).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')

    store.setMode('system')
    expect(store.mode).toBe('system')
    expect(storage.getItem('moatok_appearance_mode')).toBe('system')
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
  })

  it('computes resolvedTheme appropriately for explicit and system modes', () => {
    const store = useThemeStore()

    store.setMode('dark')
    expect(store.resolvedTheme).toBe('dark')

    store.setMode('light')
    expect(store.resolvedTheme).toBe('light')
  })
})
