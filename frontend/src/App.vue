<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import BottomNav from '@/components/BottomNav.vue'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'

const themeStore = useThemeStore()
const authStore = useAuthStore()

onMounted(() => {
  themeStore.setMode(themeStore.mode)
  authStore.init()
})
</script>

<template>
  <div class="mobile-app-shell">
    <AppHeader />
    <main class="main-content">
      <RouterView />
    </main>
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
