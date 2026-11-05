import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppearanceMode } from '@/types'

const STORAGE_KEY = 'moatok_appearance_mode'

const inMemoryStorage = new Map<string, string>()

export const mockLocalStorage: Storage = {
  getItem: (key: string) => inMemoryStorage.get(key) ?? null,
  setItem: (key: string, value: string) => {
    inMemoryStorage.set(key, String(value))
  },
  removeItem: (key: string) => {
    inMemoryStorage.delete(key)
  },
  clear: () => {
    inMemoryStorage.clear()
  },
  key: (index: number) => Array.from(inMemoryStorage.keys())[index] ?? null,
  get length() {
    return inMemoryStorage.size
  }
}

export function getSafeLocalStorage(): Storage {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage
    }
  } catch {
    // Ignore SecurityError / EPERM in restricted contexts
  }
  return mockLocalStorage
}

export const useThemeStore = defineStore('theme', () => {
  const storage = getSafeLocalStorage()
  const savedMode = (storage ? storage.getItem(STORAGE_KEY) : null) as AppearanceMode | null
  const mode = ref<AppearanceMode>(savedMode === 'light' || savedMode === 'dark' || savedMode === 'system' ? savedMode : 'system')

  const systemPrefersDark = ref<boolean>(
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false
  )

  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const updateSystemPref = (e: MediaQueryListEvent) => {
      systemPrefersDark.value = e.matches
      if (mode.value === 'system') {
        applyDomTheme('system')
      }
    }
    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', updateSystemPref)
    } else if (typeof mediaQuery.addListener === 'function') {
      mediaQuery.addListener(updateSystemPref)
    }
  }

  const resolvedTheme = computed<'light' | 'dark'>(() => {
    if (mode.value === 'system') {
      return systemPrefersDark.value ? 'dark' : 'light'
    }
    return mode.value
  })

  function applyDomTheme(targetMode: AppearanceMode) {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    if (targetMode === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', targetMode)
    }
  }

  function setMode(newMode: AppearanceMode) {
    mode.value = newMode
    const store = getSafeLocalStorage()
    if (store) {
      store.setItem(STORAGE_KEY, newMode)
    }
    applyDomTheme(newMode)
  }

  // Initialize DOM on store instantiation
  applyDomTheme(mode.value)

  return {
    mode,
    resolvedTheme,
    systemPrefersDark,
    setMode
  }
})
