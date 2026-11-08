<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ modelValue: string; label: string; id: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; 'editing': [value: boolean] }>()
const editing = ref(false)
const hour = ref('09')
const minute = ref('00')
function setEditing(value: boolean) { editing.value = value; emit('editing', value) }
function toggle() {
  if (!editing.value) [hour.value, minute.value] = props.modelValue.split(':')
  setEditing(!editing.value)
}
function apply() { emit('update:modelValue', `${hour.value}:${minute.value}`); setEditing(false) }
</script>
<template>
  <div class="automation-time-group">
    <span :id="`${id}-label`">{{ label }}</span>
    <button type="button" class="automation-time-trigger" :disabled="disabled" :aria-labelledby="`${id}-label ${id}-value`" :aria-expanded="editing" :aria-controls="`${id}-editor`" @click="toggle">
      <span :id="`${id}-value`">{{ modelValue }}</span>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
    </button>
    <div v-if="editing" :id="`${id}-editor`" class="automation-time-editor">
      <label>시 <select v-model="hour"><option v-for="h in 24" :key="h" :value="String(h - 1).padStart(2, '0')">{{ String(h - 1).padStart(2, '0') }}</option></select></label>
      <label>분 <select v-model="minute"><option v-for="m in 60" :key="m" :value="String(m - 1).padStart(2, '0')">{{ String(m - 1).padStart(2, '0') }}</option></select></label>
      <div class="automation-time-actions"><button type="button" @click="setEditing(false)">취소</button><button type="button" @click="apply">설정</button></div>
    </div>
  </div>
</template>
