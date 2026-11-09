<script setup lang="ts">

import { ref, onMounted, computed, watch } from 'vue'
import type { UserProfile } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { loginWithKakao } from '@/services/kakaoLogin'
const authStore = useAuthStore()
const authSubmitting = ref(false)
// UI snapshot only: Firebase remains the source of tokens and API permissions.
const accountSnapshotKey = 'moatok_account_display_v1'
const accountSnapshot = ref<UserProfile | null>(null)
try {
  const saved = JSON.parse(sessionStorage.getItem(accountSnapshotKey) || 'null')
  if (saved && typeof saved.uid === 'string') accountSnapshot.value = saved
} catch { /* Storage is optional for display continuity. */ }
watch(() => [authStore.status, authStore.profile] as const, () => {
  if (authStore.isAuthenticated && authStore.profile) {
    accountSnapshot.value = { uid: authStore.profile.uid, email: authStore.profile.email, role: 'user', is_admin: false }
  } else if (authStore.status === 'signed_out' || authStore.sessionExpired) {
    accountSnapshot.value = null
  }
  try {
    if (accountSnapshot.value) sessionStorage.setItem(accountSnapshotKey, JSON.stringify(accountSnapshot.value))
    else sessionStorage.removeItem(accountSnapshotKey)
  } catch { /* Do not block sign-in or sign-out when storage is unavailable. */ }
}, { immediate: true })
const displayProfile = computed(() =>
  authStore.isAuthenticated && authStore.profile ? authStore.profile :
    authStore.isLoading && !authStore.sessionExpired ? accountSnapshot.value : null)

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
              : displayProfile
              ? '인증됨'
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
      <div v-if="displayProfile" class="user-info-box">
        <div class="detail-row">
          <span class="detail-label">사용자 UID:</span>
          <span class="detail-value font-mono ellipsis">{{ displayProfile.uid }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">계정 이메일:</span>
          <span class="detail-value">{{ authStore.userEmail || displayProfile.email || (displayProfile.uid.startsWith('kakao:') ? '카카오 계정' : '익명 게스트 계정') }}</span>
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
            로그아웃
          </button>
        </div>
      </div>

      <div v-else-if="authStore.isLoading || authStore.currentUser || authStore.isAuthenticated"
        class="auth-checking-box" role="status" aria-live="polite" aria-busy="true">
        <p class="setting-caption">로그인 상태를 확인하고 있습니다…</p>
      </div>

      <!-- Signed-Out Form with Configurable Methods -->
      <div v-else class="auth-form-box">
        <p class="setting-caption">
          로그인하여 브리핑을 검토하고 보호된 백엔드 API에 접근합니다.
        </p>

        <button type="button" class="auth-primary-btn kakao-login-btn" :disabled="authSubmitting || authStore.isLoading" @click="handleKakaoAuth">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3C6.48 3 2 6.58 2 11c0 2.85 1.86 5.35 4.66 6.76l-1.18 4.3 5.02-3.13c.49.05.99.07 1.5.07 5.52 0 10-3.58 10-8S17.52 3 12 3Z"/></svg>
          {{ authSubmitting ? '처리 중…' : '카카오 로그인' }}
        </button>
        <button type="button" class="auth-primary-btn google-login-btn" :disabled="authSubmitting || authStore.isLoading" @click="handleGoogleAuth">
          <svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6C44.4 38.02 46.98 31.87 46.98 24.55Z"/><path fill="#FBBC05" d="M10.53 28.59A14.41 14.41 0 0 1 9.77 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.87 23.87 0 0 0 0 24c0 3.87.93 7.52 2.56 10.78l7.97-6.19Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"/></svg>
          {{ authSubmitting ? '처리 중…' : 'Google로 계속하기' }}
        </button>
        <p class="setting-caption">카카오 로그인 시 나와의 채팅 연결도 함께 완료됩니다. 자동 전송은 원하는 항목을 선택하고 저장하면 시작됩니다.</p>
      </div>
    </section>

      
</template>
