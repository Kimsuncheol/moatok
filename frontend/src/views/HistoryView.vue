<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessagesStore } from '@/stores/messages'
import type { ShareMessage } from '@/types'
import MessageCard from '@/components/MessageCard.vue'
import ShareModal from '@/components/ShareModal.vue'

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
  <div class="history-view">
    <section class="view-header">
      <div class="header-titles">
        <h2 class="view-title">공유 완료 이력</h2>
        <span class="count-pill">{{ messagesStore.historyCount }}건</span>
      </div>
      <p class="view-desc">
        사용자가 직접 검토하여 카카오톡으로 공유 완료한 브리핑 기록입니다.
      </p>
    </section>

    <!-- Empty State -->
    <div v-if="messagesStore.historyCount === 0" class="empty-state">
      <div class="empty-icon">📁</div>
      <h3 class="empty-title">공유 완료된 이력이 없습니다</h3>
      <p class="empty-desc">
        Pending 탭에서 대기 중인 브리핑을 확인하고 카카오톡으로 공유를 진행해보세요.
      </p>
      <RouterLink to="/" class="go-pending-btn">
        대기 브리핑 보러가기
      </RouterLink>
    </div>

    <!-- Message List -->
    <div v-else class="message-list">
      <MessageCard
        v-for="msg in messagesStore.historyMessages"
        :key="msg.id"
        :message="msg"
        @review="openReviewModal"
      />
    </div>

    <!-- Review & Re-Share Modal -->
    <ShareModal
      v-model="isModalOpen"
      :message="selectedMessage"
    />
  </div>
</template>

<style scoped>
.history-view {
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
  background-color: var(--badge-bg);
  color: var(--badge-text);
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

.go-pending-btn {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  background-color: var(--accent-action);
  color: var(--accent-action-text);
  text-decoration: none;
}

.go-pending-btn:hover {
  background-color: var(--accent-action-hover);
}
</style>
