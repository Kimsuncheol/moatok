import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SettingsView from '@/views/SettingsView.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush
  })
}))

describe('SettingsView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouterPush.mockReset()
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

    const enableBtn = wrapper.find('[aria-labelledby="notif-heading"] .setting-action-btn')
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
  it('does not display the 오늘의 영어 area in SettingsView', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()

    expect(wrapper.text()).not.toContain('오늘의 영어')
    expect(wrapper.find('.english-fetch-form').exists()).toBe(false)
  })

  it('wires register-api view to Settings view and navigates on click', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()

    const navBtn = wrapper.find('.register-api-nav-btn')
    expect(navBtn.exists()).toBe(true)
    expect(navBtn.text()).toContain('API 엔드포인트 등록 및 관리')

    await navBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/register-api')
  })

  it('does not report HTML from Hosting as a healthy backend', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('<html>App shell</html>', {status: 200}))
    const wrapper = mount(SettingsView)
    await flushPromises()
    expect(wrapper.text()).not.toContain('정상 연결됨 (/health OK)')
    expect(wrapper.text()).toContain('연결 실패')
  })

})
