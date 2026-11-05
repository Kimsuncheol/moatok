<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessagesStore } from '@/stores/messages'
import type { ShareMessage } from '@/types'
import MessageCard from '@/components/MessageCard.vue'
import ShareModal from '@/components/ShareModal.vue'
import NotificationBanner from '@/components/NotificationBanner.vue'

const messagesStore = useMessagesStore()
const selectedMessage = ref<ShareMessage | null>(null)
const isModalOpen = ref(false)

function openReviewModal(msg: ShareMessage) {
  selectedMessage.value = msg
  isModalOpen.value = true
}

onMounted(() => {
  messagesStore.fetchAll()
})
</script>

<template>
  <div class="pending-view">
    <NotificationBanner />

    <section class="view-header">
      <div class="header-titles">
        <h2 class="view-title">공유 대기 브리핑</h2>
        <span class="count-pill">{{ messagesStore.pendingCount }}건</span>
      </div>
      <p class="view-desc">
        수집된 콘텐츠를 검토하고 카카오톡 대상 채팅방으로 직접 공유하세요.
      </p>
    </section>

    <!-- Empty State -->
    <div v-if="messagesStore.pendingCount === 0" class="empty-state">
      <div class="empty-icon">✓</div>
      <h3 class="empty-title">공유 대기 브리핑이 없습니다</h3>
      <p class="empty-desc">
        현재 검토할 새 콘텐츠가 없습니다. 백엔드 스케줄러가 새 RSS 및 소스를 수집하면 이곳에 등록됩니다.
      </p>
      <button
        type="button"
        class="refresh-inline-btn"
        :disabled="messagesStore.refreshing"
        @click="messagesStore.fetchAll(true)"
      >
        새로고침 확인
      </button>
    </div>

    <!-- Message List -->
    <div v-else class="message-list">
      <MessageCard
        v-for="msg in messagesStore.pendingMessages"
        :key="msg.id"
        :message="msg"
        @review="openReviewModal"
      />
    </div>

    <!-- Review & Share Modal -->
    <ShareModal
      v-model="isModalOpen"
      :message="selectedMessage"
    />
  </div>
</template>

<style scoped>
.pending-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.view-header {
  padding: 16px 16px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-titles {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.count-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
}

.view-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
  margin: 16px;
  background-color: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: 12px;
  gap: 10px;
}

.empty-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  max-width: 320px;
}

.refresh-inline-btn {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
}

.refresh-inline-btn:hover {
  background-color: var(--bg-surface-hover);
}
</style>
