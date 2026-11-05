import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'
import { useMessagesStore } from '@/stores/messages'

const dummyComponent = { template: '<div></div>' }

describe('BottomNav Component', () => {
  let router: any

  beforeEach(async () => {
    setActivePinia(createPinia())
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'pending', component: dummyComponent },
        { path: '/history', name: 'history', component: dummyComponent },
        { path: '/settings', name: 'settings', component: dummyComponent }
      ]
    })
    router.push('/')
    await router.isReady()
  })

  it('renders bottom navigation tabs for Pending, History, and Settings', () => {
    const wrapper = mount(BottomNav, {
      global: {
        plugins: [router]
      }
    })

    const tabs = wrapper.findAll('.nav-tab')
    expect(tabs).toHaveLength(3)

    const labels = tabs.map((t) => t.find('.nav-label').text())
    expect(labels).toContain('Pending')
    expect(labels).toContain('History')
    expect(labels).toContain('Settings')
  })

  it('displays the pending badge count when pending messages exist', async () => {
    const messagesStore = useMessagesStore()
    messagesStore.pendingMessages = [
      {
        id: 'msg-1',
        title: 'Title 1',
        body: 'Body 1',
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: 'msg-2',
        title: 'Title 2',
        body: 'Body 2',
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ]

    const wrapper = mount(BottomNav, {
      global: {
        plugins: [router]
      }
    })

    const pendingBadge = wrapper.find('.pending-badge')
    expect(pendingBadge.exists()).toBe(true)
    expect(pendingBadge.text()).toBe('2')
  })
})
