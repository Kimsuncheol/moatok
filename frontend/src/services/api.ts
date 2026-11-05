import type { ShareMessage, UserProfile } from '@/types'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : 'http://localhost:8080')
).replace(/\/$/, '')

let tokenProvider: (() => Promise<string | null>) | null = null

export function setTokenProvider(provider: () => Promise<string | null>) {
  tokenProvider = provider
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (tokenProvider) {
    try {
      const token = await tokenProvider()
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
    } catch (e) {
      console.warn('Failed to retrieve auth token for request', e)
    }
  }

  const response = await fetch(url, {
    ...options,
    headers
  })

  if (!response.ok) {
    let errorDetail = response.statusText
    try {
      const errorJson = await response.json()
      errorDetail = errorJson.message || errorJson.error || response.statusText
    } catch {
      // ignore json parse error
    }
    throw new Error(`API Error [${response.status}]: ${errorDetail}`)
  }

  return response.json() as Promise<T>
}

export const api = {
  async getProfile(): Promise<{ user: UserProfile }> {
    return request<{ user: UserProfile }>('/api/v1/auth/me')
  },

  async getPendingMessages(limit = 50): Promise<{ messages: ShareMessage[]; count: number }> {
    return request<{ messages: ShareMessage[]; count: number }>(`/api/v1/messages?status=pending&limit=${limit}`)
  },

  async getHistoryMessages(limit = 50): Promise<{ messages: ShareMessage[]; count: number }> {
    // Fetches messages with status shared or shared_by_user
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
