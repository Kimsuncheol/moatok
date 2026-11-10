<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import BottomNav from '@/components/BottomNav.vue'
import ReloadPrompt from '@/components/ReloadPrompt.vue'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { useMessagesStore } from '@/stores/messages'
import { checkKakaoDeliveries } from '@/services/kakaoDelivery'

const themeStore = useThemeStore()
const authStore = useAuthStore()
const messagesStore = useMessagesStore()
let deliveryTimer: ReturnType<typeof setInterval>
let checkingDelivery = false
async function checkDelivery() {
  if (document.visibilityState === 'hidden' || checkingDelivery) return
  checkingDelivery = true
  try {
    await checkKakaoDeliveries(async id => {
      if (!await messagesStore.fetchById(id)) return false
      return !!await messagesStore.markAsShared(id, 'kakao_verified_webhook')
    })
  } finally { checkingDelivery = false }
}

onMounted(() => {
  themeStore.setMode(themeStore.mode)
  authStore.init()
  void checkDelivery()
  window.addEventListener('focus', checkDelivery)
  document.addEventListener('visibilitychange', checkDelivery)
  deliveryTimer = setInterval(checkDelivery, 10_000)
})

onUnmounted(() => {
  clearInterval(deliveryTimer)
  window.removeEventListener('focus', checkDelivery)
  document.removeEventListener('visibilitychange', checkDelivery)
})
</script>

<template>
  <div class="mobile-app-shell">
    <AppHeader />
    <main class="main-content">
      <RouterView />
    </main>
    <ReloadPrompt />
    <BottomNav />
  </div>
</template>

<style scoped>
.mobile-app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: var(--bg-page);
}

.main-content {
  flex: 1;
  padding-bottom: calc(64px + var(--sab));
  overflow-y: auto;
}
</style>
