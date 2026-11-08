<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import { ref, onMounted } from 'vue'
import { getApiBaseUrl } from '@/services/api'
const backendStatus = ref<'checking' | 'healthy' | 'unreachable'>('checking')
async function checkBackendHealth() {
  backendStatus.value = 'checking'
  try {
    const res = await fetch(`${getApiBaseUrl()}/health`, { cache: 'no-store' })
    const health = res.ok ? await res.json() : null
    if (res.ok && health?.status === 'ok') {
      backendStatus.value = 'healthy'
    } else {
      backendStatus.value = 'unreachable'
    }
  } catch {
    backendStatus.value = 'unreachable'
  }
}

onMounted(checkBackendHealth)
</script>
<template>
  <SettingsPage title="공유 정책 및 시스템 상태">
<!-- 5. System Health & Sharing Policy -->
    <section class="settings-card highlight-card" aria-labelledby="policy-heading">
      <div class="card-title-row">
        <h3 id="policy-heading" class="card-title">카카오톡 공유 정책 및 시스템 상태</h3>
        <span class="notice-tag">필독</span>
      </div>
      <div class="policy-content">
        <p class="policy-lead">
          <strong>자동 전송은 동의한 계정의 나와의 채팅에서만 지원합니다.</strong>
        </p>
        <ul class="policy-list">
          <li>
            <strong>사용자 주도 전송:</strong> 카카오 플랫폼 운영 정책 및 계정 안전을 위해, 사용자가 직접 내용을 검토한 후 대상 오픈채팅방이나 친구를 선택하여 공유하는 방식을 준수합니다.
          </li>
          <li>
            <strong>안전한 백엔드 역할:</strong> Python Flask 백엔드는 RSS 수집, 사실 기반 요약 포맷팅, Firestore 중복 방지 저장 및 PWA 푸시 알림까지만 자동으로 수행합니다.
          </li>
          <li>
            <strong>백엔드 연결 상태:</strong>
            <span class="font-mono">
              {{ backendStatus === 'healthy' ? '✓ 정상 연결됨 (/health OK)' : backendStatus === 'checking' ? '확인 중...' : '연결 실패' }}
            </span>
          </li>
        </ul>
      </div>
    </section>
  </SettingsPage>
</template>
