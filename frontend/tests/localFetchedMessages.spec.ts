import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'
import { useMessagesStore, LOCAL_MESSAGES_KEY } from '@/stores/messages'
import { useEndpointsStore } from '@/stores/endpoints'
import { api, englishScraperApi } from '@/services/api'
import PendingView from '@/views/PendingView.vue'
import type { ShareMessage } from '@/types'
vi.mock('vue-router', () => ({ useRouter: () => ({push: vi.fn()}) }))
const card = (): ShareMessage => ({id:'new', endpoint_id:'ep-1', title:'Real lesson', body:'Full English lesson', target_url:'https://www.chosun.com/lesson-one/', status:'pending', fetch_status:'success', kakao_shared:false, created_at:new Date().toISOString(), updated_at:new Date().toISOString()})
let values: Map<string,string>
beforeEach(() => {
  vi.restoreAllMocks()
  values = new Map()
  Object.defineProperty(window, 'localStorage', { configurable:true, value:{ getItem:(key:string)=>values.get(key) ?? null, setItem:(key:string,value:string)=>values.set(key,value), clear:()=>values.clear() } })
  setActivePinia(createPinia())
  vi.spyOn(api,'getPendingMessages').mockResolvedValue({messages:[],count:0})
  vi.spyOn(api,'getAllMessages').mockResolvedValue({messages:[],count:0})
})
describe('Fetched card persistence and Pending navigation', () => {
  it('preserves a fetched card through empty backend refreshes and app restart', async () => {
    let store = useMessagesStore()
    store.upsertLocalMessage(card())
    await store.fetchPending()
    await store.fetchAll(true)
    expect(store.pendingMessages.map(m=>m.title)).toEqual(['Real lesson'])
    setActivePinia(createPinia())
    store = useMessagesStore()
    expect((await store.fetchById(store.pendingMessages[0].id))?.body).toBe('Full English lesson')
    await store.fetchPending(true)
    expect(store.pendingCount).toBe(1)
  })
  it('keeps local cards visible when Pending mounting encounters an API failure', async () => {
    const store = useMessagesStore()
    store.upsertLocalMessage(card())
    vi.mocked(api.getPendingMessages).mockRejectedValue(new Error('unauthorized'))
    const wrapper = mount(PendingView)
    await flushPromises()
    expect(wrapper.text()).toContain('Real lesson')
    expect(wrapper.find('.error-state-card').exists()).toBe(false)
  })
  it('deduplicates repeat fetches while retaining different lesson days', () => {
    const store = useMessagesStore()
    store.upsertLocalMessage(card())
    store.upsertLocalMessage(card())
    store.upsertLocalMessage({...card(),target_url:'https://www.chosun.com/lesson-two/'})
    expect(store.pendingCount).toBe(2)
  })
  it('does not resurrect shared local cards after refresh or reload', async () => {
    let store = useMessagesStore()
    store.upsertLocalMessage(card())
    await store.markAsShared(store.pendingMessages[0].id)
    setActivePinia(createPinia())
    store = useMessagesStore()
    await store.fetchPending()
    await store.fetchHistory()
    expect(store.pendingCount).toBe(0)
    expect(store.historyCount).toBe(1)
  })
  it('supports endpoint fetch, Pending mount, and restored app state', async () => {
    vi.spyOn(englishScraperApi,'fetchUrl').mockResolvedValue({status:'fetched',lesson:{url:card().target_url!,fields:{expression:'Real lesson',english_dialogue:'Full English lesson'},missing_sections:[]}})
    const endpoint = useEndpointsStore().endpoints[0]
    expect((await useEndpointsStore().triggerFetch(endpoint.id,true)).success).toBe(true)
    setActivePinia(createPinia())
    const wrapper = mount(PendingView)
    await flushPromises()
    expect(wrapper.text()).toContain('Real lesson')
    expect(wrapper.text()).toContain('Full English lesson')
  })
  it('handles corrupt storage and unavailable storage without hiding fetched data', () => {
    values.set(LOCAL_MESSAGES_KEY,'invalid JSON')
    const store = useMessagesStore()
    window.localStorage.setItem = () => {throw new Error('quota')}
    store.upsertLocalMessage(card())
    expect(store.pendingCount).toBe(1)
    expect(store.storageWarning).toBeTruthy()
  })
  it('preserves a card fetched while an older server request is in flight', async () => {
    let resolve!: (value: {messages: ShareMessage[];count:number}) => void
    vi.mocked(api.getPendingMessages).mockReturnValue(new Promise(done => {resolve = done}))
    const store = useMessagesStore()
    const pending = store.fetchPending()
    store.upsertLocalMessage(card())
    resolve({messages:[],count:0})
    await pending
    expect(store.pendingCount).toBe(1)
  })
  it('updates an already-open Pending store after another tab saves a card', () => {
    const store = useMessagesStore()
    values.set(LOCAL_MESSAGES_KEY, JSON.stringify([card()]))
    window.dispatchEvent(new StorageEvent('storage', {key:LOCAL_MESSAGES_KEY}))
    expect(store.pendingMessages.map(m=>m.title)).toEqual(['Real lesson'])
  })

})
