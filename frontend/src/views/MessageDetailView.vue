<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessagesStore } from '@/stores/messages'
import { useAuthStore } from '@/stores/auth'
import { initiateKakaoShare } from '@/services/kakao'
import type { ShareMessage } from '@/types'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const messagesStore = useMessagesStore()
const authStore = useAuthStore()

const message = ref<ShareMessage | null>(null)
const loading = ref(true)

// Admin editing state
const isEditing = ref(false)
const editTitle = ref('')
const editText = ref('')
const isSaving = ref(false)
const editError = ref<string | null>(null)
const saveSuccess = ref(false)

// Kakao sharing state
const isSharing = ref(false)
const shareFeedback = ref<string | null>(null)
const isMarkingShared = ref(false)

function extractDomain(url?: string): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

const sourceName = computed(() => {
  if (!message.value) return ''
  return (
    message.value.source_name ||
    message.value.items?.[0]?.source_name ||
    extractDomain(message.value.target_url) ||
    '출처 미정'
  )
})

const isPending = computed(() => {
  if (!message.value) return false
  return message.value.status === 'pending' || !message.value.kakao_shared
})

const statusLabel = computed(() => {
  if (!message.value) return ''
  if (message.value.kakao_shared) return '카카오톡 공유 완료'
  switch (message.value.status) {
    case 'shared':
    case 'shared_by_user':
      return '카카오톡 공유 완료'
    case 'notified':
      return '푸시 알림 발송됨'
    case 'failed':
      return '실패'
    case 'archived':
      return '보관됨'
    case 'pending':
    default:
      return '공유 대기'
  }
})

const formattedCreatedDate = computed(() => {
  if (!message.value?.created_at) return ''
  try {
    const d = new Date(message.value.created_at)
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  } catch {
    return message.value.created_at
  }
})

const formattedSharedDate = computed(() => {
  if (!message.value?.shared_by_user_at) return null
  try {
    const d = new Date(message.value.shared_by_user_at)
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  } catch {
    return message.value.shared_by_user_at
  }
})

onMounted(async () => {
  loading.value = true
  try {
    message.value = await messagesStore.fetchById(props.id)
  } finally {
    loading.value = false
  }
})

function goBack() {
  if (typeof window !== 'undefined' && window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

// 1. Admin Edit Actions
function startEditing() {
  if (!message.value) return
  editTitle.value = message.value.title
  editText.value = message.value.body
  editError.value = null
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  editError.value = null
}

async function saveAdminEdit() {
  if (!message.value) return
  if (!editText.value.trim()) {
    editError.value = '공유 문구 내용을 입력해주세요.'
    return
  }

  isSaving.value = true
  editError.value = null

  try {
    const updated = await messagesStore.updateMessage(message.value.id, {
      title: editTitle.value.trim() || message.value.title,
      body: editText.value.trim()
    })
    if (updated) {
      message.value = { ...message.value, ...updated }
      isEditing.value = false
      saveSuccess.value = true
      setTimeout(() => {
        saveSuccess.value = false
      }, 4000)
    }
  } catch (err: any) {
    editError.value = err.message || '문구 수정에 실패했습니다.'
  } finally {
    isSaving.value = false
  }
}

// 2. KakaoTalk Share Action (User-Initiated)
async function handleKakaoShare() {
  if (!message.value) return
  isSharing.value = true
  shareFeedback.value = null

  try {
    // Delegates to dedicated Kakao service module
    const result = await initiateKakaoShare(message.value)

    // IMPORTANT:
    // We DO NOT mark the message as delivered merely because the share button was clicked.
    // The user must review in KakaoTalk and select the recipient.
    shareFeedback.value = result.notice || '카카오톡 공유 창이 열렸습니다. 전송할 대상 채팅방을 직접 선택해주세요.'
  } catch (err: any) {
    shareFeedback.value = err.message || '카카오톡 공유를 시작하지 못했습니다.'
  } finally {
    isSharing.value = false
  }
}

// 3. Explicit Mark as Shared by User
async function handleConfirmShared() {
  if (!message.value) return
  isMarkingShared.value = true
  try {
    const updated = await messagesStore.markAsShared(message.value.id, 'kakaotalk_web_pwa')
    if (updated) {
      message.value = updated
      shareFeedback.value = '카카오톡 전송 완료로 기록되었습니다.'
    }
  } catch (err: any) {
    shareFeedback.value = err.message || '공유 상태 업데이트에 실패했습니다.'
  } finally {
    isMarkingShared.value = false
  }
}
</script>

<template>
  <main class="detail-view">
    <!-- Top Bar Navigation -->
    <nav class="top-nav" aria-label="상세 페이지 뒤로가기">
      <button
        type="button"
        class="back-btn"
        aria-label="이전 목록으로 돌아가기"
        @click="goBack"
      >
        <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        <span>목록으로 돌아가기</span>
      </button>
    </nav>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="loading-state"
      role="status"
      aria-live="polite"
    >
      <div class="spinner" aria-hidden="true" />
      <span>브리핑 정보를 불러오는 중입니다...</span>
    </div>

    <!-- Not Found State -->
    <div
      v-else-if="!message"
      class="not-found-state"
      role="alert"
    >
      <div class="not-found-icon">?</div>
      <h2 class="not-found-title">브리핑을 찾을 수 없습니다</h2>
      <p class="not-found-desc">요청하신 브리핑이 존재하지 않거나 삭제되었습니다.</p>
      <button type="button" class="back-home-btn" @click="router.push('/')">
        공유 대기 목록으로 이동
      </button>
    </div>

    <!-- Message Detail Content -->
    <article v-else class="detail-article">
      <!-- Success Toast Banner -->
      <div v-if="saveSuccess" class="notice-banner success-banner" role="status">
        ✓ 관리자 권한으로 브리핑 공유 문구가 성공적으로 수정되었습니다.
      </div>

      <!-- Header: Status, Source, and Creation Time -->
      <header class="detail-header">
        <div class="status-source-row">
          <span
            class="status-badge"
            :class="isPending ? 'badge-pending' : 'badge-shared'"
            :aria-label="`공유 상태: ${statusLabel}`"
          >
            {{ statusLabel }}
          </span>

          <span
            v-if="sourceName"
            class="source-badge"
            :title="`출처: ${sourceName}`"
            :aria-label="`출처: ${sourceName}`"
          >
            <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
            <span class="source-text">{{ sourceName }}</span>
          </span>
        </div>

        <time
          class="creation-time"
          :datetime="message.created_at"
          :title="`수집 및 생성 일시: ${message.created_at}`"
        >
          {{ formattedCreatedDate }}
        </time>
      </header>

      <!-- 1. Article Title -->
      <h1 class="article-title">{{ message.title }}</h1>

      <!-- 2. Share Text (Read or Edit Mode for Admins) -->
      <section class="share-text-section" aria-label="카카오톡 공유 문구">
        <div class="section-title-row">
          <h2 class="section-label">카카오톡 공유 문구 (Share Text)</h2>

          <!-- Admin Edit Toggle Button -->
          <button
            v-if="authStore.isAdmin && !isEditing"
            type="button"
            class="admin-edit-btn"
            @click="startEditing"
          >
            <svg class="edit-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            <span>문구 편집 (Admin)</span>
          </button>
        </div>

        <!-- Admin Edit Form -->
        <div v-if="isEditing" class="edit-form-card">
          <div class="edit-field">
            <label for="edit-title-input" class="field-label">제목 수정</label>
            <input
              id="edit-title-input"
              v-model="editTitle"
              type="text"
              class="field-input"
              placeholder="브리핑 제목"
              maxlength="100"
              :disabled="isSaving"
            />
          </div>

          <div class="edit-field">
            <div class="field-header">
              <label for="edit-body-textarea" class="field-label">공유 문구 내용</label>
              <span class="char-count">{{ editText.length }} / 500자</span>
            </div>
            <textarea
              id="edit-body-textarea"
              v-model="editText"
              rows="6"
              class="field-textarea"
              placeholder="카카오톡으로 공유될 문구를 입력하세요"
              maxlength="500"
              :disabled="isSaving"
            />
          </div>

          <div v-if="editError" class="edit-error-text" role="alert">
            ✕ {{ editError }}
          </div>

          <div class="edit-buttons-row">
            <button
              type="button"
              class="save-btn"
              :disabled="isSaving"
              @click="saveAdminEdit"
            >
              {{ isSaving ? '저장 중...' : '수정 내용 저장' }}
            </button>
            <button
              type="button"
              class="cancel-btn"
              :disabled="isSaving"
              @click="cancelEditing"
            >
              취소
            </button>
          </div>
        </div>

        <!-- Read-Only Share Text Display -->
        <div v-else class="share-text-box">
          <pre class="share-text-content">{{ message.body }}</pre>
        </div>
      </section>

      <!-- 3. Original Article URL -->
      <section v-if="message.target_url" class="article-url-section" aria-label="원문 기사 링크">
        <span class="url-label" aria-hidden="true">🔗 원문 기사:</span>
        <a
          :href="message.target_url"
          target="_blank"
          rel="noopener noreferrer"
          class="url-link"
          :aria-label="`${message.title} 원문 웹페이지 열기 (새 창)`"
        >
          {{ message.target_url }}
        </a>
      </section>

      <!-- 4. Delivery Status & Kakao Policy Clarification -->
      <section class="delivery-status-section" aria-label="공유 배포 상태">
        <div class="status-detail-box">
          <div class="detail-item">
            <span class="item-label">현재 상태:</span>
            <span class="item-value font-semibold">{{ statusLabel }}</span>
          </div>
          <div v-if="formattedSharedDate" class="detail-item">
            <span class="item-label">공유 일시:</span>
            <span class="item-value">{{ formattedSharedDate }}</span>
          </div>
          <div v-if="message.last_share_channel" class="detail-item">
            <span class="item-label">공유 채널:</span>
            <span class="item-value font-mono">{{ message.last_share_channel }}</span>
          </div>
        </div>

        <!-- Architectural Boundary Explanation -->
        <div class="sharing-policy-notice">
          <p class="policy-notice-text">
            ℹ️ <strong>사용자 주도 전송 원칙:</strong>
            카카오톡 공유 버튼을 클릭하면 카카오톡 앱 또는 공유 시트가 실행됩니다.
            플랫폼 보안 규정에 따라 <strong>버튼 클릭만으로는 메시지가 배포 완료로 처리되지 않으며</strong>,
            카카오톡에서 전송을 마친 후 아래의 <em>'공유 완료로 기록하기'</em>를 눌러 완료 상태를 확정할 수 있습니다.
          </p>
        </div>
      </section>

      <!-- Share Action Result Feedback Notice -->
      <div v-if="shareFeedback" class="share-feedback-notice" role="status" aria-live="polite">
        {{ shareFeedback }}
      </div>

      <!-- 5. Prominent "Share to KakaoTalk" Action Button -->
      <div class="action-buttons-group">
        <button
          type="button"
          class="prominent-kakao-btn"
          :disabled="isSharing"
          aria-label="카카오톡으로 공유하기 (카카오 공유 창 열기)"
          @click="handleKakaoShare"
        >
          <svg class="kakao-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 3C6.477 3 2 6.477 2 10.767c0 2.766 1.879 5.187 4.717 6.558-.207.77-.747 2.784-.855 3.21-.136.536.196.529.412.385.17-.113 2.7-1.83 3.793-2.573.62.086 1.265.133 1.933.133 5.523 0 10-3.477 10-7.713C22 6.477 17.523 3 12 3z"/>
          </svg>
          <span>{{ isSharing ? '카카오톡 연결 중...' : '카카오톡으로 공유하기' }}</span>
        </button>

        <!-- Explicit User Confirmation Button to Mark as Shared -->
        <button
          v-if="isPending"
          type="button"
          class="mark-shared-btn"
          :disabled="isMarkingShared"
          aria-label="카카오톡 전송 완료로 기록하기"
          @click="handleConfirmShared"
        >
          {{ isMarkingShared ? '상태 저장 중...' : '카카오톡 전송 완료로 기록하기' }}
        </button>

        <div v-else class="already-shared-badge" role="status">
          ✓ 카카오톡으로 공유 완료된 브리핑입니다.
        </div>
      </div>
    </article>
  </main>
</template>

<style scoped>
.detail-view {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 40px;
  max-width: 480px;
  margin: 0 auto;
}

.top-nav {
  display: flex;
  align-items: center;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px 4px;
  min-height: 44px;
}

.back-btn:hover {
  color: var(--text-primary);
}

.back-icon {
  width: 16px;
  height: 16px;
}

.loading-state,
.not-found-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 16px;
  gap: 12px;
  color: var(--text-muted);
  text-align: center;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-action);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.not-found-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.not-found-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.not-found-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.back-home-btn {
  margin-top: 8px;
  padding: 10px 18px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.detail-article {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-sm);
}

.notice-banner {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.4;
}

.success-banner {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
  color: var(--text-primary);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.status-source-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-pending {
  background-color: var(--badge-pending-bg);
  color: var(--badge-pending-text);
}

.badge-shared {
  background-color: var(--badge-bg);
  color: var(--badge-text);
}

.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
  color: var(--text-secondary);
  max-width: 160px;
}

.meta-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.source-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.creation-time {
  font-size: 12px;
  color: var(--text-muted);
}

.article-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.4px;
}

/* Share Text Section */
.share-text-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

.admin-edit-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 3px 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.admin-edit-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.edit-icon {
  width: 12px;
  height: 12px;
}

.share-text-box {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 14px;
}

.share-text-content {
  font-family: var(--font-sans);
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Edit Form */
.edit-form-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 14px;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
}

.char-count {
  font-size: 10.5px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.field-input,
.field-textarea {
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-default);
  background-color: var(--bg-surface);
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  outline: none;
}

.field-textarea {
  resize: vertical;
  line-height: 1.5;
}

.field-input:focus,
.field-textarea:focus {
  border-color: var(--border-strong);
}

.edit-error-text {
  font-size: 11.5px;
  color: var(--text-primary);
  font-weight: 600;
}

.edit-buttons-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.save-btn {
  flex: 1;
  padding: 9px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-size: 12.5px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn {
  padding: 9px 14px;
  border-radius: 6px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

/* Original Article URL */
.article-url-section {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  overflow: hidden;
}

.url-label {
  color: var(--text-muted);
  flex-shrink: 0;
  font-weight: 600;
}

.url-link {
  color: var(--text-secondary);
  text-decoration: underline;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-link:hover {
  color: var(--text-primary);
}

/* Delivery Status & Policy */
.delivery-status-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-detail-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background-color: var(--bg-surface-elevated);
  border-radius: 8px;
  font-size: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.item-label {
  color: var(--text-muted);
}

.item-value {
  color: var(--text-primary);
}

.font-semibold {
  font-weight: 600;
}

.font-mono {
  font-family: var(--font-mono);
}

.sharing-policy-notice {
  padding: 10px 12px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-strong);
  border-radius: 8px;
}

.policy-notice-text {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-muted);
}

.share-feedback-notice {
  padding: 10px 12px;
  border-radius: 8px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  font-size: 12px;
  color: var(--text-primary);
  line-height: 1.45;
}

/* Action Buttons */
.action-buttons-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.prominent-kakao-btn {
  width: 100%;
  padding: 14px 16px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  border-radius: 10px;
  font-size: 15px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: none;
  cursor: pointer;
  min-height: 48px;
  box-shadow: var(--shadow-sm);
  transition: opacity 0.15s ease;
}

.prominent-kakao-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.prominent-kakao-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kakao-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.mark-shared-btn {
  width: 100%;
  padding: 11px 14px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  cursor: pointer;
  min-height: 44px;
  transition: all 0.15s ease;
}

.mark-shared-btn:hover:not(:disabled) {
  border-color: var(--border-strong);
  background-color: var(--bg-surface-hover);
}

.already-shared-badge {
  text-align: center;
  padding: 10px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  background-color: var(--bg-surface-elevated);
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}
</style>
