import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AccountSettings from '@/components/AccountSettings.vue'
import { useAuthStore } from '@/stores/auth'
import type { User } from 'firebase/auth'

describe('account session restoration', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.spyOn(useAuthStore(), 'init').mockImplementation(() => {}) })
  it('never renders login buttons while restoring a saved session and profile', async () => {
    const auth = useAuthStore()
    const wrapper = mount(AccountSettings)
    expect(wrapper.find('.auth-checking-box').exists()).toBe(true)
    expect(wrapper.find('.kakao-login-btn').exists()).toBe(false)
    expect(wrapper.find('.google-login-btn').exists()).toBe(false)
    auth.user = { uid: 'saved-user', email: null } as User
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.auth-form-box').exists()).toBe(false)
    auth.profile = { uid: 'saved-user', email: null, role: 'user', is_admin: false }
    auth.status = 'authenticated'
    auth.loading = false
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.user-info-box').exists()).toBe(true)
    expect(wrapper.find('.auth-form-box').exists()).toBe(false)
    auth.loading = true
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.user-info-box').exists()).toBe(true)
  })
  it('shows login buttons after session checking confirms signed out', async () => {
    const auth = useAuthStore()
    const wrapper = mount(AccountSettings)
    auth.status = 'signed_out'
    auth.loading = false
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.kakao-login-btn').exists()).toBe(true)
    expect(wrapper.find('.google-login-btn').exists()).toBe(true)
  })
})
