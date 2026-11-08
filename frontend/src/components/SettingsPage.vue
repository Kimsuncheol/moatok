<script setup lang="ts">
defineProps<{ title: string }>()
</script>
<template>
  <div class="settings-view">
    <RouterLink to="/settings" class="settings-back-link">‹ 환경 설정</RouterLink>
    <header class="view-header"><h2 class="view-title">{{ title }}</h2></header>
    <slot />
  </div>
</template>
