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
