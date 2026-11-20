<script setup lang="ts">
withDefaults(defineProps<{ title: string; backTo?: string; backLabel?: string }>(), {
  backTo: '/settings',
  backLabel: '환경 설정'
})
</script>
<template>
  <div class="settings-view">
    <RouterLink :to="backTo" class="settings-back-link">‹ {{ backLabel }}</RouterLink>
    <header class="view-header"><h2 class="view-title">{{ title }}</h2></header>
    <slot />
  </div>
</template>
