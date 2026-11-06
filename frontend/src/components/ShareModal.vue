<script setup lang="ts">
import MyChatSend from '@/components/MyChatSend.vue'
import { ref } from 'vue'
import type { ShareMessage } from '@/types'
import { initiateKakaoShare } from '@/services/kakao'
import { useMessagesStore } from '@/stores/messages'

const props = defineProps<{
  message: ShareMessage | null
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'shared', message: ShareMessage): void
}>()

const messagesStore = useMessagesStore()
const isSharing = ref(false)
const copied = ref(false)
const noticeText = ref<string | null>(null)

function close() {
  noticeText.value = null
  copied.value = false
  emit('update:modelValue', false)
}

async function copyBodyText() {
  if (!props.message) return
  try {
    await navigator.clipboard.writeText(props.message.body)
    copied.value = true
    noticeText.value = '클립보드에 전체 내용이 복사되었습니다.'
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
  }
}

async function handleKakaoShare() {
  if (!props.message || isSharing.value) return
  isSharing.value = true
  noticeText.value = null

  try {
    const res = await initiateKakaoShare(props.message)
    noticeText.value = res.notice

    // Mark as shared in backend and Pinia store
    const updated = await messagesStore.markAsShared(props.message.id, res.channel)
    if (updated) {
      emit('shared', updated)
    }
  } catch (err: any) {
    noticeText.value = '공유 중 오류가 발생했습니다. 수동으로 복사해주세요.'
  } finally {
    isSharing.value = false
  }
}
</script>

<template>
  <div v-if="modelValue && message" class="modal-backdrop" @click.self="close">
    <div class="modal-sheet" role="dialog" aria-modal="true" :aria-labelledby="'modal-title-' + message.id">
      <div class="sheet-handle" @click="close" />

      <div class="sheet-header">
        <h2 :id="'modal-title-' + message.id" class="sheet-title">공유 내용 검토</h2>
        <button type="button" class="close-btn" aria-label="닫기" @click="close">
          ✕
        </button>
      </div>

      <!-- Critical Notice Banner -->
      <div class="notice-banner" role="alert">
        <div class="notice-icon">ℹ️</div>
        <div class="notice-body">
          <strong class="notice-title">사용자 직접 공유 원칙</strong>
          <p class="notice-desc">
            Moatok은 카카오톡 채팅방에 <strong>자동으로 게시하지 않습니다.</strong>
            공유 버튼을 누르면 카카오톡 앱이 열리며, 전송할 <strong>대상 오픈채팅방이나 친구를 직접 선택</strong>하셔야 합니다.
          </p>
        </div>
      </div>

      <div class="content-preview">
        <div class="preview-header">
          <span class="preview-label">카카오톡 전송 본문 미리보기</span>
          <button type="button" class="copy-small-btn" @click="copyBodyText">
            {{ copied ? '✓ 복사됨' : '본문 복사' }}
          </button>
        </div>
        <pre class="preview-box">{{ message.body }}</pre>
      </div>

      <div v-if="message.target_url" class="target-link-box">
        <span class="link-label">원문 링크:</span>
        <a :href="message.target_url" target="_blank" rel="noopener noreferrer" class="link-href">
          {{ message.target_url }}
        </a>
      </div>

      <div v-if="noticeText" class="feedback-notice">
        {{ noticeText }}
      </div>

      <MyChatSend :message="message" />
      <div class="sheet-actions">
        <button
          type="button"
          class="share-primary-btn"
          :disabled="isSharing"
          @click="handleKakaoShare"
        >
          <span v-if="isSharing" class="spinner" />
          <span>카카오톡으로 공유하기 (선택창 열기)</span>
        </button>

        <button type="button" class="cancel-btn" @click="close">
          닫기
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.modal-sheet {
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-default);
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
  padding: 16px;
  padding-bottom: calc(16px + var(--sab));
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.sheet-handle {
  width: 40px;
  height: 4px;
  background-color: var(--border-strong);
  border-radius: 2px;
  margin: 0 auto 4px auto;
  cursor: pointer;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sheet-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.4px;
}

.close-btn {
  font-size: 16px;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 4px;
}

.close-btn:hover {
  color: var(--text-primary);
}

.notice-banner {
  display: flex;
  gap: 10px;
  padding: 12px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.notice-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.notice-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.notice-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.notice-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.content-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.copy-small-btn {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.copy-small-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.preview-box {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px;
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.target-link-box {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  overflow: hidden;
}

.link-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.link-href {
  color: var(--text-secondary);
  text-decoration: underline;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feedback-notice {
  font-size: 12.5px;
  font-weight: 500;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px dashed var(--border-strong);
  color: var(--text-primary);
  text-align: center;
}

.sheet-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.share-primary-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 13px;
  border-radius: 8px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  font-size: 14.5px;
  font-weight: 700;
  transition: all 0.15s ease;
}

.share-primary-btn:hover {
  background-color: var(--accent-action-hover);
}

.share-primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  background-color: transparent;
  color: var(--text-muted);
  font-size: 13.5px;
  font-weight: 500;
}

.cancel-btn:hover {
  color: var(--text-primary);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--accent-action-text);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
