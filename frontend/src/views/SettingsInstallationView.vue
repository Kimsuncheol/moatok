<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import { ref, computed } from 'vue'
// Platform detection for PWA guidance
const detectedPlatform = computed<'android' | 'ios' | 'desktop'>(() => {
  if (typeof navigator === 'undefined') return 'desktop'
  const ua = navigator.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
    return 'ios'
  }
  if (/Android/.test(ua)) {
    return 'android'
  }
  return 'desktop'
})

const activePlatformTab = ref<'android' | 'ios' | 'desktop'>('desktop')

activePlatformTab.value = detectedPlatform.value
</script>
<template>
  <SettingsPage title="앱 설치 안내">
<!-- 3. Platform-Specific PWA Installation Guidance -->
    <section class="settings-card" aria-labelledby="pwa-guide-heading">
      <div class="card-title-row">
        <h3 id="pwa-guide-heading" class="card-title">PWA 앱 설치 안내 (Platform Guide)</h3>
        <span class="info-badge">PWA 가이드</span>
      </div>
      <p class="setting-caption">
        모아톡을 홈 화면에 앱 형태로 설치하여 독립형 전체화면 실행과 원활한 푸시 알림을 경험하세요.
      </p>

      <!-- Platform Selection Tabs -->
      <nav class="platform-tabs" aria-label="기기별 설치 안내 선택">
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'android' }"
          @click="activePlatformTab = 'android'"
        >
          <span>🤖 Android</span>
          <span v-if="detectedPlatform === 'android'" class="detected-badge">현재 기기</span>
        </button>
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'ios' }"
          @click="activePlatformTab = 'ios'"
        >
          <span>🍎 iOS (Safari)</span>
          <span v-if="detectedPlatform === 'ios'" class="detected-badge">현재 기기</span>
        </button>
        <button
          type="button"
          class="platform-tab-btn"
          :class="{ active: activePlatformTab === 'desktop' }"
          @click="activePlatformTab = 'desktop'"
        >
          <span>💻 Desktop (PC)</span>
          <span v-if="detectedPlatform === 'desktop'" class="detected-badge">현재 기기</span>
        </button>
      </nav>

      <!-- Platform Guides -->
      <div class="platform-guide-content">
        <!-- Android Guide -->
        <div v-if="activePlatformTab === 'android'" class="platform-card">
          <div class="platform-card-header">
            <strong>Android (Chrome / Samsung Internet) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>Chrome 또는 Samsung Internet 브라우저로 Moatok에 접속합니다.</li>
            <li>브라우저 상단 또는 하단의 <strong>더보기 메뉴(⋮)</strong>를 누릅니다.</li>
            <li><strong>'앱 설치'</strong> 또는 <strong>'홈 화면에 추가'</strong>를 선택합니다.</li>
            <li>홈 화면에 추가된 Moatok 아이콘을 눌러 독립형 앱(Standalone)으로 실행합니다.</li>
          </ol>
        </div>

        <!-- iOS Guide -->
        <div v-if="activePlatformTab === 'ios'" class="platform-card ios-card">
          <div class="platform-card-header">
            <strong>iOS / iPadOS (Safari) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>반드시 <strong>Safari 브라우저</strong>로 접속합니다 (카카오톡 인앱 브라우저 등에서는 설치 불가).</li>
            <li>Safari 하단 툴바의 <strong>공유 버튼(네모 위 화살표 모양)</strong>을 탭합니다.</li>
            <li>메뉴를 아래로 스크롤하여 <strong>'홈 화면에 추가'</strong>를 선택하고 완료합니다.</li>
            <li>홈 화면에 생성된 <strong>모아톡 아이콘을 눌러 실행</strong>합니다.</li>
          </ol>
          <div class="ios-alert-box">
            <strong class="ios-alert-title">⚠️ iOS 필수 안내 (iOS 16.4+)</strong>
            <p class="ios-alert-desc">
              Apple 정책상 <strong>iOS 16.4 이상</strong>에서만 PWA 웹 푸시 알림이 지원되며, <strong>반드시 홈 화면에 추가한 후 홈 화면 아이콘으로 실행한 상태</strong>에서만 푸시 알림 권한을 허용하고 수신할 수 있습니다. 일반 Safari 브라우저 탭에서는 알림 기능이 차단됩니다.
            </p>
          </div>
        </div>

        <!-- Desktop Guide -->
        <div v-if="activePlatformTab === 'desktop'" class="platform-card">
          <div class="platform-card-header">
            <strong>Desktop (Chrome / Edge / Safari) 설치 방법</strong>
          </div>
          <ol class="step-list">
            <li>Chrome 또는 Edge 브라우저 주소창 우측의 <strong>설치 아이콘(⊕)</strong>을 클릭합니다.</li>
            <li>또는 브라우저 메뉴(⋮) > <strong>'Moatok 설치'</strong>를 선택합니다.</li>
            <li>설치 후 데스크톱 독립 창 및 작업 표시줄에 고정하여 편리하게 사용합니다.</li>
          </ol>
        </div>
      </div>
    </section>

      </SettingsPage>
</template>
