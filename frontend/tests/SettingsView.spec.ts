import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SettingsView from '@/views/SettingsView.vue'
import { englishScraperApi } from '@/services/api'
import { useNotificationsStore } from '@/stores/notifications'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'

describe('SettingsView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' })
    } as Response)
  })

  it('displays notification permission status clearly', async () => {
    const notifStore = useNotificationsStore()
    notifStore.permission = 'default'
    notifStore.isSupported = true

    const wrapper = mount(SettingsView)
    await flushPromises()

    // 1. Shows permission status indicator
    expect(wrapper.text()).toContain('미설정 (Default)')
    expect(wrapper.text()).toContain('권한 요청 필요')

    // Change to granted
    notifStore.permission = 'granted'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('허용됨 (Active)')
    expect(wrapper.text()).toContain('알림 수신 가능')

    // Change to denied
    notifStore.permission = 'denied'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('차단됨 (Denied)')
    expect(wrapper.text()).toContain('브라우저에서 차단됨')
    expect(wrapper.find('.denied-guidance-box').exists()).toBe(true)
  })

  it('provides an action button to enable notifications when supported', async () => {
    const notifStore = useNotificationsStore()
    notifStore.permission = 'default'
    notifStore.isSupported = true
    const registerSpy = vi.spyOn(notifStore, 'requestPermissionAndRegister').mockResolvedValue(true)

    const wrapper = mount(SettingsView)
    await flushPromises()

    const enableBtn = wrapper.find('.setting-action-btn')
    expect(enableBtn.exists()).toBe(true)
    expect(enableBtn.text()).toContain('푸시 알림 권한 허용하기')

    await enableBtn.trigger('click')
    await flushPromises()

    expect(registerSpy).toHaveBeenCalled()
    expect(wrapper.find('.notif-feedback-box').exists()).toBe(true)
  })

  it('provides system, light, and dark appearance modes as a list without a dropdown (<select>)', async () => {
    const themeStore = useThemeStore()
    const wrapper = mount(SettingsView)
    await flushPromises()

    // Requirement 1: NO dropdown (<select>)
    expect(wrapper.find('select').exists()).toBe(false)

    // Requirement 2: Appearance modes provided AS A LIST
    const list = wrapper.find('ul.appearance-mode-list')
    expect(list.exists()).toBe(true)

    const items = list.findAll('li.appearance-mode-item')
    expect(items).toHaveLength(3)

    const itemTitles = items.map((i) => i.find('.mode-name').text())
    expect(itemTitles.some((t) => t.includes('시스템 설정 (System)'))).toBe(true)
    expect(itemTitles.some((t) => t.includes('라이트 모드 (Light)'))).toBe(true)
    expect(itemTitles.some((t) => t.includes('다크 모드 (Dark)'))).toBe(true)

    // Clicking an item switches appearance mode
    const darkItem = items.find((i) => i.find('.mode-name').text().includes('다크'))
    expect(darkItem).toBeDefined()
    await darkItem?.trigger('click')
    expect(themeStore.mode).toBe('dark')
    expect(darkItem?.classes()).toContain('selected')

    const lightItem = items.find((i) => i.find('.mode-name').text().includes('라이트'))
    expect(lightItem).toBeDefined()
    await lightItem?.trigger('click')
    expect(themeStore.mode).toBe('light')
    expect(lightItem?.classes()).toContain('selected')

    const systemItem = items.find((i) => i.find('.mode-name').text().includes('시스템'))
    expect(systemItem).toBeDefined()
    await systemItem?.trigger('click')
    expect(themeStore.mode).toBe('system')
    expect(systemItem?.classes()).toContain('selected')
  })

  it('shows platform-specific PWA installation guidance for Android, iOS, and Desktop', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()

    const platformTabs = wrapper.findAll('.platform-tab-btn')
    expect(platformTabs.length).toBeGreaterThanOrEqual(3)

    // Android Tab
    const androidTab = platformTabs.find((t) => t.text().includes('Android'))
    await androidTab?.trigger('click')
    expect(wrapper.text()).toContain('Android (Chrome / Samsung Internet) 설치 방법')
    expect(wrapper.text()).toContain('더보기 메뉴(⋮)')

    // iOS Tab with iOS 16.4+ and Home Screen execution requirement
    const iosTab = platformTabs.find((t) => t.text().includes('iOS'))
    await iosTab?.trigger('click')
    expect(wrapper.text()).toContain('iOS / iPadOS (Safari) 설치 방법')
    expect(wrapper.text()).toContain('공유 버튼(네모 위 화살표 모양)')
    expect(wrapper.text()).toContain('iOS 16.4 이상')
    expect(wrapper.text()).toContain('홈 화면에 추가한 후 홈 화면 아이콘으로 실행')

    // Desktop Tab
    const desktopTab = platformTabs.find((t) => t.text().includes('Desktop'))
    await desktopTab?.trigger('click')
    expect(wrapper.text()).toContain('Desktop (Chrome / Edge / Safari) 설치 방법')
  })

  it('provides logout when user is authenticated', async () => {
    const authStore = useAuthStore()
    vi.spyOn(authStore, 'init').mockImplementation(() => {})
    authStore.user = { uid: 'u_test_1', email: 'test@example.com' } as any
    authStore.profile = { uid: 'u_test_1', email: 'test@example.com', role: 'user', is_admin: false }
    authStore.status = 'authenticated'
    authStore.loading = false

    const logoutSpy = vi.spyOn(authStore, 'logout').mockResolvedValue(undefined)

    const wrapper = mount(SettingsView)
    await flushPromises()

    const logoutBtn = wrapper.find('.logout-btn')
    expect(logoutBtn.exists()).toBe(true)
    expect(logoutBtn.text()).toContain('로그아웃')

    await logoutBtn.trigger('click')
    expect(logoutSpy).toHaveBeenCalledTimes(1)
  })
  it('fetches multiple URLs and continues after an individual failure', async () => {
    const auth = useAuthStore()
    auth.profile = { uid: 'admin', email: null, role: 'admin', is_admin: true }
    const fetchLesson = vi.spyOn(englishScraperApi, 'fetchUrl').mockRejectedValueOnce(new Error('First URL failed')).mockResolvedValue({
      status: 'created', message_id: 'msg-1',
      lesson: { url: 'https://www.chosun.com/example', fields: { expression: 'Hello there' }, missing_sections: [] }
    })
    const wrapper = mount(SettingsView)
    await flushPromises()
    auth.profile = { uid: 'admin', email: null, role: 'admin', is_admin: true }
    await wrapper.vm.$nextTick()
    await wrapper.find('#english-url-0').setValue('https://www.chosun.com/example')
    await wrapper.find('.add-english-url').trigger('click')
    await wrapper.find('#english-url-1').setValue('https://www.chosun.com/second')
    await wrapper.find('.english-fetch-form').trigger('submit')
    await flushPromises()
    expect(fetchLesson).toHaveBeenNthCalledWith(1, { url: 'https://www.chosun.com/example' })
    expect(fetchLesson).toHaveBeenNthCalledWith(2, { url: 'https://www.chosun.com/second' })
    expect(wrapper.text()).toContain('First URL failed')
    expect(wrapper.text()).toContain('Hello there')
    expect(wrapper.text()).toContain('공유 대기에 저장했습니다')
  })

})
