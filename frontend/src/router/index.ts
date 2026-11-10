import { createRouter, createWebHistory } from 'vue-router'
import PendingView from '@/views/PendingView.vue'
import HistoryView from '@/views/HistoryView.vue'
import SettingsView from '@/views/SettingsView.vue'
import MessageDetailView from '@/views/MessageDetailView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'pending',
      component: PendingView
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },
    { path: '/settings/appearance', name: 'settings-appearance', component: () => import('@/views/SettingsAppearanceView.vue') },
    { path: '/settings/notifications', name: 'settings-notifications', component: () => import('@/views/SettingsNotificationsView.vue') },
    { path: '/settings/installation', name: 'settings-installation', component: () => import('@/views/SettingsInstallationView.vue') },
    { path: '/settings/account', name: 'settings-account', component: () => import('@/views/SettingsAccountView.vue') },
    { path: '/settings/system', name: 'settings-system', component: () => import('@/views/SettingsSystemView.vue') },
    { path: '/settings/openchat', redirect: '/settings' },
    { path: '/settings/my-chat', name: 'settings-my-chat', component: () => import('@/views/SettingsMyChatView.vue') },
    {
      path: '/register-api',
      name: 'register-api',
      component: () => import('@/views/RegisterEndpointView.vue')
    },
    {
      path: '/messages/:id',
      name: 'message-detail',
      component: MessageDetailView,
      props: true
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

export default router
