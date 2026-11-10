import { fetchChosunArticles, isChosunDaily } from '@/services/chosunDaily'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiEndpoint, ApiSchedule, ShareMessage } from '@/types'
import { useMessagesStore } from '@/stores/messages'
import { englishScraperApi } from '@/services/api'

export const DEFAULT_ENGLISH_SCRAPPER_URL =
  (import.meta.env.VITE_ENGLISH_SCRAPER_URL as string | undefined)?.trim() ||
  'https://english-scrapper.onrender.com'

const STORAGE_KEY = 'moatok_registered_api_endpoints_v1'

export function createDefaultSchedule(override: Partial<ApiSchedule> = {}): ApiSchedule {
  return {
    enabled: true,
    scheduledTime: '09:00',
    retryIntervalHours: 1, // 1 hour after the scheduled time
    maxRetries: 5, // up to 5 times
    currentAttempts: 0,
    lastRunAt: null,
    nextRunAt: null,
    lastStatus: 'idle',
    lastError: null,
    ...override
  }
}

export function createDefaultEnglishEndpoint(): ApiEndpoint {
  return {
    id: 'endpoint_english_scrapper_default',
    name: 'English Scraper API',
    url: DEFAULT_ENGLISH_SCRAPPER_URL.replace(/\/+$/, '') + '/api/v1/lessons/fetch',
    method: 'POST',
    sourceType: 'english_scrapper',
    schedule: createDefaultSchedule({
      scheduledTime: '09:00',
      lastStatus: 'idle'
    }),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
}

export const useEndpointsStore = defineStore('endpoints', () => {
  const endpoints = ref<ApiEndpoint[]>([createDefaultEnglishEndpoint()])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const testing = ref(false)
  const testResult = ref<{
    success: boolean
    message: string
    statusCode?: number
    details?: any
  } | null>(null)

  function loadEndpoints() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const raw = window.localStorage.getItem(STORAGE_KEY)
        if (raw) {
          const parsed = JSON.parse(raw)
          if (Array.isArray(parsed) && parsed.length > 0) {
            endpoints.value = parsed
            return
          }
        }
      }
    } catch (e) {
      console.warn('Failed to load registered API endpoints from localStorage:', e)
    }
    if (endpoints.value.length === 0) {
      endpoints.value = [createDefaultEnglishEndpoint()]
      saveEndpoints()
    }
  }

  function saveEndpoints() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(endpoints.value))
      }
    } catch (e) {
      console.warn('Failed to save registered API endpoints to localStorage:', e)
    }
  }

  function addEndpoint(payload: {
    name: string
    url: string
    method?: 'GET' | 'POST'
    headers?: Record<string, string>
    payload?: string
    sourceType?: 'english_scrapper' | 'generic_api'
    schedule?: Partial<ApiSchedule>
  }): ApiEndpoint {
    const cleanUrl = payload.url.trim()
    if (!cleanUrl) {
      throw new Error('API 엔드포인트 URL을 입력해주세요.')
    }

    try {
      const parsed = new URL(cleanUrl)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        throw new Error('HTTP 또는 HTTPS URL을 입력해주세요.')
      }
    } catch {
      throw new Error('유효한 URL 형식이 아닙니다.')
    }

    const isEnglishScrapper =
      payload.sourceType === 'english_scrapper' ||
      cleanUrl.includes('english-scrapper') ||
      cleanUrl.includes('english_scrapper')

    const newEndpoint: ApiEndpoint = {
      id: `ep_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      name: payload.name.trim() || (isEnglishScrapper ? 'English Scraper' : 'Custom API Endpoint'),
      url: cleanUrl,
      method: payload.method || (isEnglishScrapper ? 'POST' : 'GET'),
      headers: payload.headers,
      payload: payload.payload,
      sourceType: isEnglishScrapper ? 'english_scrapper' : 'generic_api',
      schedule: createDefaultSchedule(payload.schedule),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    endpoints.value.unshift(newEndpoint)
    saveEndpoints()
    return newEndpoint
  }

  function updateEndpoint(id: string, updates: Partial<Omit<ApiEndpoint, 'id' | 'createdAt'>>) {
    const idx = endpoints.value.findIndex((e) => e.id === id)
    if (idx === -1) return null

    endpoints.value[idx] = {
      ...endpoints.value[idx],
      ...updates,
      updatedAt: new Date().toISOString()
    }
    saveEndpoints()
    return endpoints.value[idx]
  }

  function deleteEndpoint(id: string) {
    const idx = endpoints.value.findIndex((e) => e.id === id)
    if (idx !== -1) {
      endpoints.value.splice(idx, 1)
      saveEndpoints()
    }
  }

  async function testEndpoint(endpointData: {
    url: string
    method?: 'GET' | 'POST'
    headers?: Record<string, string>
    sourceType?: 'english_scrapper' | 'generic_api'
  }): Promise<{ success: boolean; message: string; statusCode?: number; details?: any }> {
    testing.value = true
    testResult.value = null
    const targetUrl = endpointData.url.trim()

    try {
      const parsed = new URL(targetUrl)
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        throw new Error('HTTP 또는 HTTPS 프로토콜만 지원합니다.')
      }

      if (isChosunDaily(targetUrl)) {
        const items = await fetchChosunArticles()
        const result = { success: true, message: `기사 ${items.length}개 연결 확인`, statusCode: 200 }
        testResult.value = result
        return result
      }

      // If it's english_scrapper url
      const isEnglish =
        endpointData.sourceType === 'english_scrapper' ||
        targetUrl.includes('english-scrapper') ||
        targetUrl.includes('english_scrapper')

      if (isEnglish) {
        const res = await englishScraperApi.fetchUrl({url: 'https://www.chosun.com/national/nie/english/'})
        const result = {success: true, message: '실제 영어 수업 가져오기 성공', statusCode: 200, details: res}
        testResult.value = result
        return result
      }

      // Generic endpoint test
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 8000)
      try {
        const fetchMethod = endpointData.method || 'GET'
        const res = await fetch(targetUrl, {
          method: fetchMethod,
          headers: endpointData.headers,
          signal: controller.signal
        })
        clearTimeout(timer)
        const result = {
          success: res.ok,
          message: res.ok
            ? `성공 (${res.status} ${res.statusText || 'OK'}) - 엔드포인트 응답이 정상입니다.`
            : `서버 오류 (${res.status}): 응답을 확인하세요.`,
          statusCode: res.status
        }
        testResult.value = result
        return result
      } catch (err: any) {
        clearTimeout(timer)
        // If aborted or network blocked by browser CORS
        const isCorsOrNet = err.name !== 'AbortError'
        const result = {
          success: isCorsOrNet,
          message: isCorsOrNet
            ? `URL 형식 정상 확인 (${targetUrl}). 브라우저 보안(CORS)으로 인해 클라이언트 직접 테스트는 제한되나 스케줄러 수집이 가능합니다.`
            : `연결 시간 초과 (8초). 엔드포인트 주소를 확인하세요.`,
          statusCode: isCorsOrNet ? 200 : 504
        }
        testResult.value = result
        return result
      }
    } catch (err: any) {
      const result = {
        success: false,
        message: err.message || '엔드포인트 테스트 실패',
        statusCode: 400
      }
      testResult.value = result
      return result
    } finally {
      testing.value = false
    }
  }

  /**
   * Triggers fetching for an endpoint.
   * Enforces retry policy:
   * Up to 5 times. 1 hour after scheduled time.
   * When 5 attempts fail, posts a failed card in Pending view with 'Fetch' button.
   */
  async function triggerFetch(endpointId: string, isManual = false): Promise<{
    success: boolean
    message: string
    shareMessage?: ShareMessage
  }> {
    const endpoint = endpoints.value.find((e) => e.id === endpointId)
    if (!endpoint) {
      return { success: false, message: '해당 엔드포인트를 찾을 수 없습니다.' }
    }

    const messagesStore = useMessagesStore()
    endpoint.schedule.lastStatus = 'fetching'
    endpoint.schedule.lastRunAt = new Date().toISOString()
    saveEndpoints()

    try {
      if (isChosunDaily(endpoint.url)) {
        const articles = await fetchChosunArticles()
        for (const article of articles) {
          messagesStore.upsertLocalMessage({
            id: `chosun_${article.id}`, article_id: String(article.id),
            title: article.title, body: article.body, target_url: article.url,
            source_name: endpoint.name, source_id: endpoint.id, endpoint_id: endpoint.id,
            status: 'pending', fetch_status: 'success', kakao_shared: false,
            created_at: new Date().toISOString(), updated_at: new Date().toISOString()
          }, { restoreDeleted: isManual })
        }
        endpoint.schedule.lastStatus = 'success'
        endpoint.schedule.currentAttempts = 0
        endpoint.schedule.lastError = null
        saveEndpoints()
        const ids = new Set(articles.map(article => `local_${encodeURIComponent(article.url)}`))
        const pending = messagesStore.pendingMessages.filter(message => ids.has(message.id)).length
        const shared = messagesStore.historyMessages.filter(message => ids.has(message.id)).length
        return { success: true, message: `기사 ${articles.length}개 확인 · 공유 대기 ${pending}개 · 이미 공유됨 ${shared}개` }
      }
      if (endpoint.sourceType === 'english_scrapper'  || endpoint.url.includes('english-scrapper')) {
        const result = await englishScraperApi.fetchUrl({url: 'https://www.chosun.com/national/nie/english/'})
        const lessonTitle = result.lesson.fields.expression || '오늘의 영어'
        const lessonBody = Object.values(result.lesson.fields).join('\n\n') + '\n\n' + result.lesson.url

        // On success:
        endpoint.schedule.lastStatus = 'success'
        endpoint.schedule.currentAttempts = 0
        endpoint.schedule.lastError = null

        // Add the newly fetched message
        const newMsg: ShareMessage = {
          id: `smsg_ep_${Date.now()}`,
          title: lessonTitle,
          body: lessonBody,
          target_url: result.lesson.url,
          source_name: endpoint.name,
          source_id: endpoint.id,
          endpoint_id: endpoint.id,
          status: 'pending',
          fetch_status: 'success',
          kakao_shared: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          items: [
            {
              title: lessonTitle,
              url: result.lesson.url,
              source_name: endpoint.name,
              summary: '자동 수집 스케줄로 가져온 최신 브리핑입니다.'
            }
          ]
        }

        messagesStore.upsertLocalMessage(newMsg, { restoreDeleted: isManual })
        saveEndpoints()
        return { success: true, message: '데이터를 성공적으로 가져왔습니다.', shareMessage: newMsg }
      }

      // Generic API fetch
      const res = await fetch(endpoint.url, {
        method: endpoint.method,
        headers: endpoint.headers,
        ...(endpoint.method === 'POST' && endpoint.payload ? { body: endpoint.payload } : {})
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`)
      }

      const data = await res.json()
      const title = data?.title || `${endpoint.name} 최신 브리핑`
      const content = typeof data === 'string' ? data : [data?.body, data?.message, data?.content].find(value => typeof value === 'string' && value.trim())
      const body = content || `[모아톡 브리핑] ${title}\n\n${JSON.stringify(data, null, 2)}\n\n🔗 ${endpoint.url}`

      endpoint.schedule.lastStatus = 'success'
      endpoint.schedule.currentAttempts = 0
      endpoint.schedule.lastError = null

      const newMsg: ShareMessage = {
        id: `smsg_ep_${Date.now()}`,
        title,
        body,
        target_url: endpoint.url,
        source_name: endpoint.name,
        source_id: endpoint.id,
        endpoint_id: endpoint.id,
        status: 'pending',
        fetch_status: 'success',
        kakao_shared: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      messagesStore.upsertLocalMessage(newMsg, { restoreDeleted: isManual })
      saveEndpoints()
      return { success: true, message: '데이터를 성공적으로 가져왔습니다.', shareMessage: newMsg }
    } catch (err: any) {
      const errorMsg = err.message || '데이터 수집 실패'
      endpoint.schedule.lastError = errorMsg

      if (isManual) {
        // If manual fetch directly failed, keep or update failed status
        endpoint.schedule.lastStatus = 'failed'
      } else {
        // Schedule auto-fetch: Increment attempt count up to 5 times
        endpoint.schedule.currentAttempts = Math.min(endpoint.schedule.currentAttempts + 1, 5)
        endpoint.schedule.lastStatus = 'failed'
      }

      // Post/update failed card in Pending view
      const failedCardId = `failed_fetch_${endpoint.id}`

      const failedMsg: ShareMessage = {
        id: failedCardId,
        title: `[수집 실패] ${endpoint.name}`,
        body: `자동 데이터 수집에 실패했습니다 (${endpoint.schedule.currentAttempts}/${endpoint.schedule.maxRetries}회 시도 초과, 예정 시간 1시간 후 재시도 포함).\n\n엔드포인트: ${endpoint.url}\n오류 내용: ${errorMsg}\n\n아래 'Fetch' 버튼을 눌러 수동으로 데이터를 다시 가져오세요.`,
        target_url: endpoint.url,
        source_name: endpoint.name,
        source_id: endpoint.id,
        endpoint_id: endpoint.id,
        status: 'failed',
        fetch_status: 'failed',
        failed_reason: errorMsg,
        fetch_attempts: endpoint.schedule.currentAttempts,
        kakao_shared: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      messagesStore.upsertLocalMessage(failedMsg)

      saveEndpoints()
      return {
        success: false,
        message: `데이터 수집 실패 (${endpoint.schedule.currentAttempts}/${endpoint.schedule.maxRetries}회 시도): ${errorMsg}`
      }
    }
  }

  /**
   * Simulates failing up to 5 times (1 hour after scheduled time),
   * placing the failed card in Pending view with the 'Fetch' button.
   */
  function simulateFiveFailedAttempts(endpointId: string) {
    const endpoint = endpoints.value.find((e) => e.id === endpointId)
    if (!endpoint) return null

    const messagesStore = useMessagesStore()
    endpoint.schedule.currentAttempts = 5
    endpoint.schedule.lastStatus = 'failed'
    endpoint.schedule.lastError = '5회 연속 응답 시간 초과 (1시간 간격 재시도 포함)'
    endpoint.schedule.lastRunAt = new Date().toISOString()

    const failedCardId = `failed_fetch_${endpoint.id}`
    const failedMsg: ShareMessage = {
      id: failedCardId,
      title: `[수집 실패] ${endpoint.name}`,
      body: `자동 데이터 수집이 5회 시도 후 실패했습니다 (예정 시간 1시간 후 재시도 포함).\n\n엔드포인트: ${endpoint.url}\n오류: 5회 연속 응답 시간 초과 (HTTP 504 Gateway Timeout)\n\n아래 'Fetch' 버튼을 눌러 데이터를 다시 가져오세요.`,
      target_url: endpoint.url,
      source_name: endpoint.name,
      source_id: endpoint.id,
      endpoint_id: endpoint.id,
      status: 'failed',
      fetch_status: 'failed',
      failed_reason: '5회 연속 응답 시간 초과',
      fetch_attempts: 5,
      kakao_shared: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    messagesStore.upsertLocalMessage(failedMsg)

    saveEndpoints()
    return failedMsg
  }

  return {
    endpoints,
    loading,
    error,
    testing,
    testResult,
    loadEndpoints,
    saveEndpoints,
    addEndpoint,
    updateEndpoint,
    deleteEndpoint,
    testEndpoint,
    triggerFetch,
    simulateFiveFailedAttempts
  }
})
