import { it, expect } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMessagesStore } from '@/stores/messages'

it('persists deletion and prevents fetched cards from returning', async () => {
  localStorage.clear()
  setActivePinia(createPinia())
  const store = useMessagesStore()
  const message = { id: 'test', title: 'Article', body: 'Text', target_url: 'https://example.com/article', endpoint_id: 'ep', fetch_status: 'success' as const, status: 'pending' as const, kakao_shared: false, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
  store.upsertLocalMessage(message)
  store.deleteMessage(message.id)
  store.upsertLocalMessage(message)
  expect(store.pendingMessages.some(m => m.id === message.id)).toBe(false)
  setActivePinia(createPinia())
  const reloaded = useMessagesStore()
  expect(await reloaded.fetchById(message.id)).toBeNull()
})
