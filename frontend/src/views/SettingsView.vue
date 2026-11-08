<script setup lang="ts">
import AccountSettings from '@/components/AccountSettings.vue'
const sections = [
  { path: '/register-api', title: 'API 엔드포인트 등록 및 관리', description: '외부 API와 자동 수집 스케줄을 관리합니다.' },
  { path: '/settings/openchat', title: '오픈채팅 예약 전송', description: '등록된 API 데이터로 메시지를 작성하고 예약 파일을 만듭니다.' },
  { path: '/settings/my-chat', title: '나와의 채팅 자동 전송', description: '새 콘텐츠와 매일 모음의 자동 전송을 설정합니다.' },
  { path: '/settings/appearance', title: '화면 테마', description: '시스템, 라이트, 다크 모드를 선택합니다.' },
  { path: '/settings/notifications', title: '푸시 알림', description: '알림 권한과 기기 등록을 관리합니다.' },
  { path: '/settings/installation', title: 'PWA 앱 설치 안내', description: '기기별 홈 화면 설치 방법을 확인합니다.' },
  { path: '/settings/system', title: '공유 정책 및 시스템 상태', description: '공유 정책과 백엔드 연결 상태를 확인합니다.' }
]
</script>
<template>
  <div class="settings-view">
    <header class="view-header"><h2 class="view-title">환경 설정</h2><p class="view-desc">관리할 항목을 선택하세요.</p></header>
    <AccountSettings />
    <nav class="settings-navigation" aria-label="설정 항목">
      <RouterLink v-for="item in sections" :key="item.path" :to="item.path" class="settings-card settings-nav-link" :class="{ 'register-api-nav-btn': item.path === '/register-api' }">
        <div><h3 class="card-title">{{ item.title }}</h3><p class="setting-caption">{{ item.description }}</p></div>
        <svg class="settings-nav-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
      </RouterLink>
    </nav>
  </div>
</template>
