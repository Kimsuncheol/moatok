import { fetchEnglishLesson } from './englishLessons'
import type { ShareMessage, UserProfile } from '@/types'

export class ApiError extends Error {
  status: number
  code?: string
  details?: any

  constructor(status: number, message: string, code?: string, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export type TokenProvider = (forceRefresh?: boolean) => Promise<string | null>
export type SessionExpiredHandler = (error: ApiError) => void

let customBaseUrl: string | null = null
let tokenProvider: TokenProvider | null = null
let sessionExpiredHandler: SessionExpiredHandler | null = null

export function getApiBaseUrl(): string {
  if (customBaseUrl !== null) {
    return customBaseUrl
  }
  const envUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  if (envUrl) {
    return envUrl.replace(/\/+$/, '')
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin.replace(/\/+$/, '')
  }
  return 'http://localhost:8080'
}

export function setApiBaseUrl(url: string | null) {
  customBaseUrl = url !== null ? url.trim().replace(/\/+$/, '') : null
}

export function setTokenProvider(provider: TokenProvider | null) {
  tokenProvider = provider
}

export function setOnSessionExpired(handler: SessionExpiredHandler | null) {
  sessionExpiredHandler = handler
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl()
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = `${baseUrl}${path}`
  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  let hadToken = false
  if (tokenProvider) {
    try {
      const token = await tokenProvider(false)
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
        hadToken = true
      }
    } catch (e) {
      console.warn('Failed to retrieve auth token for request', e)
    }
  }

  let response = await fetch(url, {
    ...options,
    headers
  })

  // Handle expired sessions and retry on 401 when a token provider is available
  if (response.status === 401 && tokenProvider) {
    let isExpiredOrUnauthorized = false
    try {
      const clone = response.clone()
      const errorJson = await clone.json()
      if (errorJson?.code === 'token_expired' || errorJson?.code === 'invalid_token' || hadToken) {
        isExpiredOrUnauthorized = true
      }
    } catch {
      if (hadToken) isExpiredOrUnauthorized = true
    }

    if (isExpiredOrUnauthorized) {
      try {
        const refreshedToken = await tokenProvider(true)
        if (refreshedToken) {
          headers.set('Authorization', `Bearer ${refreshedToken}`)
          response = await fetch(url, {
            ...options,
            headers
          })
        }
      } catch (refreshErr) {
        console.warn('Token force-refresh attempt failed:', refreshErr)
      }
    }
  }

  if (!response.ok) {
    let errorDetail = response.statusText
    let errorCode: string | undefined
    let errorJson: any = null

    try {
      errorJson = await response.json()
      errorDetail = errorJson.message || errorJson.error || response.statusText
      errorCode = errorJson.code
    } catch {
      // response body was not valid JSON
    }

    const apiError = new ApiError(
      response.status,
      `API Error [${response.status}]: ${errorDetail}`,
      errorCode,
      errorJson
    )

    if (response.status === 401) {
      sessionExpiredHandler?.(apiError)
    }

    throw apiError
  }

  const contentType = response.headers?.get('content-type') || ''
  if (contentType.includes('text/html')) {
    throw new ApiError(503, '가져오기 서버가 아직 연결되지 않았습니다. 서버 배포 및 API 연결이 필요합니다.', 'backend_not_configured')
  }
  try {
    return await response.json() as T
  } catch {
    throw new ApiError(502, '서버에서 올바른 데이터를 받지 못했습니다. 잠시 후 다시 시도해 주세요.', 'invalid_api_response')
  }
}

export const api = {
  getApiBaseUrl,
  setApiBaseUrl,
  setTokenProvider,
  setOnSessionExpired,

  async getProfile(): Promise<{ user: UserProfile }> {
    return request<{ user: UserProfile }>('/api/v1/auth/me')
  },

  async getPendingMessages(limit = 50): Promise<{ messages: ShareMessage[]; count: number }> {
    return request<{ messages: ShareMessage[]; count: number }>(`/api/v1/messages?status=pending&limit=${limit}`)
  },

  async getHistoryMessages(limit = 50): Promise<{ messages: ShareMessage[]; count: number }> {
    return request<{ messages: ShareMessage[]; count: number }>(`/api/v1/messages?status=shared&limit=${limit}`)
  },

  async getAllMessages(limit = 100): Promise<{ messages: ShareMessage[]; count: number }> {
    return request<{ messages: ShareMessage[]; count: number }>(`/api/v1/messages?limit=${limit}`)
  },

  async getMessageById(messageId: string): Promise<{ message: ShareMessage }> {
    return request<{ message: ShareMessage }>(`/api/v1/messages/${encodeURIComponent(messageId)}`)
  },

  async markMessageShared(
    messageId: string,
    shareChannel = 'kakaotalk_web_pwa'
  ): Promise<{ message: ShareMessage }> {
    return request<{ message: ShareMessage }>(`/api/v1/messages/${encodeURIComponent(messageId)}/mark-shared`, {
      method: 'POST',
      body: JSON.stringify({ share_channel: shareChannel })
    })
  },

  async reportShareAttempt(
    messageId: string,
    payload: { channel: string } = { channel: 'kakao_sdk' }
  ): Promise<{ message_id: string; recorded: boolean; channel: string; share_attempt_count: number }> {
    return request<{ message_id: string; recorded: boolean; channel: string; share_attempt_count: number }>(
      `/api/v1/messages/${encodeURIComponent(messageId)}/share-attempt`,
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    )
  },

  async updateShareMessage(
    messageId: string,
    payload: { title?: string; body?: string; target_url?: string; status?: string }
  ): Promise<{ share_message: ShareMessage }> {
    return request<{ share_message: ShareMessage }>(`/api/v1/admin/share-messages/${encodeURIComponent(messageId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
  },

  async registerFcmDevice(payload: {
    fcm_token: string
    device_id?: string
    platform?: string
  }): Promise<{ message: string; device_id: string }> {
    return request<{ message: string; device_id: string }>('/api/v1/devices/fcm-token', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }
}


export interface EnglishLesson {
  fields: Record<string, string>
  missing_sections: string[]
  upstream_updated_at?: string
  url: string
}
export const englishScraperApi = {
  fetchUrl: fetchEnglishLesson,
  review: () => request<{ lessons: EnglishLesson[] }>('/api/v1/admin/integrations/english-scrapper/lessons'),
  status: () => request<{ enabled: boolean; url: string; last_sync: Record<string, unknown> | null }>('/api/v1/admin/integrations/english-scrapper'),
  sync: (offset = 0) => request<{ created: number; held: number; failed: number; next_offset: number | null }>('/api/v1/admin/integrations/english-scrapper/sync', { method: 'POST', body: JSON.stringify({ offset }) }),
  lesson: (id: string) => request<{ lesson: EnglishLesson }>(`/api/v1/share-messages/${encodeURIComponent(id)}/english-lesson`)
}
