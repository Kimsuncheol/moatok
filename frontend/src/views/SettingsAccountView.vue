<script setup lang="ts">
import SettingsPage from '@/components/SettingsPage.vue'
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { loginWithKakao } from '@/services/kakaoLogin'
const authStore = useAuthStore()
const authSubmitting = ref(false)
async function handleKakaoAuth() {
  if (authSubmitting.value) return
  authSubmitting.value = true
  try { await authStore.loginWithCustomToken(await loginWithKakao()) }
  catch (error) { authStore.error = error instanceof Error ? error.message : '카카오 로그인에 실패했습니다.' }
  finally { authSubmitting.value = false }
}

async function handleGoogleAuth() {
  authSubmitting.value = true
  try {
    await authStore.loginWithGoogle()
  } catch {
    // Error is captured in authStore.error
  } finally {
    authSubmitting.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
}

onMounted(() => authStore.init())
</script>
<template>
  <SettingsPage title="사용자 계정">
<!-- 4. User Account & Logout -->
    <section class="settings-card" aria-labelledby="auth-heading">
      <div class="card-title-row">
        <h3 id="auth-heading" class="card-title">사용자 계정 (Firebase Auth)</h3>
        <span
          class="status-indicator"
          :class="{
            active: authStore.isAuthenticated,
            inactive: !authStore.isAuthenticated && !authStore.sessionExpired,
            expired: authStore.sessionExpired
          }"
        >
          {{
            authStore.sessionExpired
              ? '세션 만료'
              : authStore.isLoading
              ? '확인 중'
              : authStore.isAuthenticated
              ? (authStore.isAdmin ? '관리자 (Admin)' : '인증됨')
              : '미인증'
          }}
        </span>
      </div>

      <!-- Expired Session Alert Banner -->
      <div v-if="authStore.sessionExpired" class="auth-alert expired-alert">
        <div class="alert-icon">⚠️</div>
        <div class="alert-body">
          <strong>세션이 만료되었습니다</strong>
          <p>보안을 위해 다시 로그인해주세요.</p>
        </div>
      </div>

      <!-- Error Alert Banner -->
      <div v-if="authStore.error" class="auth-alert error-alert">
        <div class="alert-icon">✕</div>
        <div class="alert-body">
          <p>{{ authStore.error }}</p>
        </div>
        <button
          type="button"
          class="alert-dismiss-btn"
          aria-label="오류 메시지 닫기"
          @click="authStore.clearError"
        >
          ✕
        </button>
      </div>

      <!-- Authenticated User Profile with Logout -->
      <div v-if="authStore.isAuthenticated && authStore.profile" class="user-info-box">
        <div class="detail-row">
          <span class="detail-label">사용자 UID:</span>
          <span class="detail-value font-mono ellipsis">{{ authStore.profile.uid }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 이메일:</span>
          <span class="detail-value">{{ authStore.userEmail || (authStore.userUid?.startsWith('kakao:') ? '카카오 계정' : '익명 게스트 계정') }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 권한:</span>
          <span class="detail-value" :class="{ 'admin-badge': authStore.isAdmin }">
            {{ authStore.isAdmin ? '관리자 (Admin Custom Claim)' : '일반 사용자' }}
          </span>
        </div>

        <div class="auth-actions-row">
          <button
            type="button"
            class="logout-btn"
            :disabled="authStore.isLoading"
            aria-label="계정 로그아웃"
            @click="handleLogout"
          >
            {{ authStore.isLoading ? '처리 중...' : '로그아웃' }}
          </button>
        </div>
      </div>

      <!-- Signed-Out Form with Configurable Methods -->
      <div v-else class="auth-form-box">
        <p class="setting-caption">
          로그인하여 브리핑을 검토하고 보호된 백엔드 API에 접근합니다.
        </p>

        <button type="button" class="auth-primary-btn kakao-login-btn" :disabled="authSubmitting || authStore.isLoading" @click="handleKakaoAuth">
          {{ authSubmitting ? '처리 중…' : '카카오톡으로 로그인' }}
        </button>
        <button type="button" class="auth-primary-btn google-login-btn" :disabled="authSubmitting || authStore.isLoading" @click="handleGoogleAuth">
          {{ authSubmitting ? '처리 중…' : 'Google로 계속하기' }}
        </button>
        <p class="setting-caption">카카오 로그인 시 나와의 채팅 연결도 함께 완료됩니다. 자동 전송은 원하는 항목을 선택하고 저장하면 시작됩니다.</p>
      </div>
    </section>

      </SettingsPage>
</template>
