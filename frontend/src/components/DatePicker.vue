<script setup lang="ts">
import { computed, ref, watch } from 'vue'
const props = defineProps<{ modelValue: string; id: string; label: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const expanded = ref(false)
const month = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
watch(() => props.modelValue, value => {
  if (value) { const date = new Date(`${value}T00:00:00`); if (Number.isFinite(date.getTime())) month.value = new Date(date.getFullYear(), date.getMonth(), 1) }
}, { immediate: true })
const heading = computed(() => `${month.value.getFullYear()}년 ${month.value.getMonth() + 1}월`)
const cells = computed(() => {
  const offset = month.value.getDay()
  const days = new Date(month.value.getFullYear(), month.value.getMonth() + 1, 0).getDate()
  return Array.from({ length: Math.ceil((offset + days) / 7) * 7 }, (_, i) => i >= offset && i < offset + days ? i - offset + 1 : null)
})
function dateValue(day: number) { return `${month.value.getFullYear()}-${String(month.value.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}` }
function move(delta: number) { month.value = new Date(month.value.getFullYear(), month.value.getMonth() + delta, 1) }
function select(day: number) { emit('update:modelValue', dateValue(day)); expanded.value = false }
</script>
<template>
  <div class="date-picker">
    <span :id="`${id}-label`">{{ label }}</span>
    <button type="button" class="date-picker-trigger" :aria-labelledby="`${id}-label ${id}-value`" :aria-expanded="expanded" :aria-controls="`${id}-calendar`" @click="expanded = !expanded">
      <span :id="`${id}-value`">{{ modelValue || '날짜 선택' }}</span>
      <svg class="date-picker-chevron" :class="{ expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
    </button>
    <section v-if="expanded" :id="`${id}-calendar`" class="date-picker-calendar" :aria-labelledby="`${id}-month`">
      <div class="date-picker-month"><button type="button" aria-label="이전 달" @click="move(-1)">‹</button><strong :id="`${id}-month`" aria-live="polite">{{ heading }}</strong><button type="button" aria-label="다음 달" @click="move(1)">›</button></div>
      <div class="date-picker-grid">
        <span v-for="day in ['일', '월', '화', '수', '목', '금', '토']" :key="day" class="date-picker-weekday">{{ day }}</span>
        <template v-for="(day, index) in cells" :key="index">
          <button v-if="day" type="button" :aria-label="dateValue(day)" :aria-pressed="modelValue === dateValue(day)" @click="select(day)">{{ day }}</button><span v-else />
        </template>
      </div>
    </section>
  </div>
</template>
