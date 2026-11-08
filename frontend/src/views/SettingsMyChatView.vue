<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import MyChatAutomation from '@/components/MyChatAutomation.vue'
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore()
</script>
<template><SettingsPage title="나와의 채팅 자동 전송"><MyChatAutomation v-if="authStore.isAuthenticated" :key="authStore.userUid || 'account'" /><p v-else class="setting-caption">자동 전송을 설정하려면 <RouterLink to="/settings/account">로그인</RouterLink>하세요.</p></SettingsPage></template>
