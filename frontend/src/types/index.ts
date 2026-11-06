export type AppearanceMode = 'system' | 'light' | 'dark'

export type MessageStatus =
  | 'pending'
  | 'shared'
  | 'shared_by_user'
  | 'notified'
  | 'archived'
  | 'failed'

export interface ShareableItem {
  id?: string
  title: string
  url?: string
  source_name?: string
  summary?: string
  image_url?: string
  published_at?: string
}

export interface KakaoSharePayload {
  template_type?: string
  title?: string
  description?: string
  text?: string
  primary_web_url?: string
  button_title?: string
  image_url?: string
  requires_user_action_in_flutter?: boolean
}

export interface ShareMessage {
  id: string
  article_id?: string
  user_id?: string
  title: string
  body: string
  target_url?: string
  source_name?: string
  source_id?: string
  status: MessageStatus
  kakao_shared?: boolean
  shared_by_user_id?: string | null
  shared_by_user_at?: string | null
  last_share_channel?: string | null
  share_attempt_count?: number
  last_share_attempt_at?: string | null
  last_share_attempt_channel?: string | null
  notification_attempts?: number
  last_notification_status?: string | null
  last_notified_at?: string | null
  created_at: string
  updated_at: string
  items?: ShareableItem[]
  kakao_share_payload?: KakaoSharePayload
  fetch_status?: 'idle' | 'fetching' | 'success' | 'failed'
  endpoint_id?: string
  fetch_attempts?: number
  failed_reason?: string
}

export interface ApiSchedule {
  enabled: boolean
  scheduledTime: string
  retryIntervalHours: number
  maxRetries: number
  currentAttempts: number
  lastRunAt: string | null
  nextRunAt: string | null
  lastStatus: 'idle' | 'fetching' | 'success' | 'failed'
  lastError?: string | null
}

export interface ApiEndpoint {
  id: string
  name: string
  url: string
  method: 'GET' | 'POST'
  headers?: Record<string, string>
  payload?: string
  sourceType?: 'english_scrapper' | 'generic_api'
  schedule: ApiSchedule
  createdAt: string
  updatedAt: string
}

export interface UserProfile {
  uid: string
  email: string | null
  role: 'user' | 'admin' | string
  is_admin: boolean
}

export type AuthSignInMethod = 'email' | 'anonymous' | 'google' | 'custom'

export type AuthStatus = 'loading' | 'authenticated' | 'signed_out' | 'expired' | 'error'

export interface SignInCredentials {
  method?: AuthSignInMethod
  email?: string
  password?: string
  token?: string
}
