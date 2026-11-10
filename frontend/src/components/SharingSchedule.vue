<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import type { ShareMessage } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useSharingScheduleStore } from '@/stores/sharingSchedule'
const props = defineProps<{ message: ShareMessage }>()
const auth = useAuthStore()
const schedule = useSharingScheduleStore()
const pending = computed(() => !props.message.kakao_shared && !['shared', 'shared_by_user', 'archived', 'failed'].includes(props.message.status) && props.message.fetch_status !== 'failed')
const local = computed(() => props.message.id.startsWith('local_') || props.message.id.startsWith('smsg_sample_'))
const summary = computed(() => {
  if (local.value) return '자동 전송 예약 없음 · 직접 공유'
  if (!auth.isAuthenticated) return '전송 예정 시간: 로그인 후 확인'
  if (schedule.loading) return '전송 예정 시간 확인 중…'
  if (schedule.unavailable || !schedule.settings) return '전송 예정 시간을 확인하지 못했습니다.'
  const settings = schedule.settings
  if (!settings.connected || (!settings.on_new && !settings.daily)) return '자동 전송 예약 없음 · 직접 공유'
  const times = []
  if (settings.on_new) times.push('새 콘텐츠 수집 후 약 5분 이내')
  if (settings.daily) times.push(`매일 ${settings.daily_time} 이후 약 5분 이내 (한국 시간) · 최신 5개 모음`)
  return times.join(' / ')
})
function refresh() { if (pending.value && !local.value) void schedule.refresh() }
onMounted(() => { refresh(); window.addEventListener('focus', refresh) })
onUnmounted(() => window.removeEventListener('focus', refresh))
</script>
<template>
  <div v-if="pending" class="sharing-schedule" role="status">
    <span class="sharing-schedule-label">나와의 채팅 전송 예정</span>
    <span class="sharing-schedule-time">{{ summary }}</span>
    <span v-if="local" class="sharing-schedule-note">이 기기에만 저장된 카드는 자동 전송 대상이 아닙니다.</span>
    <span v-else-if="schedule.settings?.connected && (schedule.settings.on_new || schedule.settings.daily) && !schedule.unavailable" class="sharing-schedule-note">서버에 수집된 콘텐츠의 전송 설정입니다. 실제 전송 여부는 처리 결과에 따라 달라집니다.</span>
  </div>
</template>
