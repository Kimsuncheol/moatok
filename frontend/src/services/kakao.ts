import type { ShareMessage } from '@/types'
import { api } from '@/services/api'
import { beginKakaoDelivery, forgetKakaoDelivery } from './kakaoDelivery'

export interface ShareResult {
  success: boolean
  channel: 'kakao_sdk' | 'web_share' | 'clipboard'
  notice: string
  detailUrl?: string
  openChatNotice?: string
}

const KAKAO_JS_KEY = (import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY as string | undefined)?.trim() || ''

/**
 * Returns the application's registered canonical domain URL for a message detail page.
 *
 * CRITICAL OFFICIAL KAKAO SDK CONSTRAINT (Domain Validation / KOE101):
 * The official Kakao JavaScript SDK strictly validates that all link targets (mobileWebUrl, webUrl)
 * belong to the registered web domain configured in Kakao Developers Console ([플랫폼] > [Web] > [사이트 도메인]).
 * Direct links to external news sources (e.g. news.example.com) will trigger KOE101 errors.
 *
 * Therefore, Kakao template cards MUST link to this application's detail page on the registered domain.
 * The recipient opens the registered detail page on Moatok, which then presents the full briefing
 * and provides the direct clickable link to the original external article.
 */
export function getRegisteredMessageUrl(messageId: string): string {
  const origin =
    typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin.replace(/\/+$/, '')
      : 'http://localhost:5173'
  return `${origin}/messages/${encodeURIComponent(messageId)}`
}

/**
 * Dynamically loads the official Kakao JavaScript SDK if not already loaded.
 */
export async function loadKakaoSdkScript(timeoutMs = 1500): Promise<boolean> {
  if (typeof window === 'undefined') return false
  if (window.Kakao) return true

  // In test environments, avoid network hanging if external script is unmocked
  if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'test') {
    return false
  }

  const existingScript = document.querySelector('script[src*="kakao_js_sdk"]')
  if (existingScript) {
    return new Promise((resolve) => {
      let attempts = 0
      const interval = setInterval(() => {
        attempts++
        if (window.Kakao) {
          clearInterval(interval)
          resolve(true)
        } else if (attempts >= 15) {
          clearInterval(interval)
          resolve(false)
        }
      }, 50)
    })
  }

  return new Promise((resolve) => {
    try {
      const script = document.createElement('script')
      script.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js'
      script.integrity = 'sha384-TiCUE00h649CAMonG018J2ujOgDKW/kVWlChEuu4jK2vxfAAD0eZxzCKakxg55G4'
      script.crossOrigin = 'anonymous'
      script.async = true

      const timer = setTimeout(() => {
        resolve(!!window.Kakao)
      }, timeoutMs)

      script.onload = () => {
        clearTimeout(timer)
        resolve(!!window.Kakao)
      }
      script.onerror = () => {
        clearTimeout(timer)
        resolve(false)
      }
      document.head.appendChild(script)
    } catch {
      resolve(false)
    }
  })
}

/**
 * Initializes the official Kakao JavaScript SDK using the configured JavaScript Key.
 */
export function initKakaoSdk(): boolean {
  if (typeof window === 'undefined') return false
  if (!window.Kakao) return false

  if (!window.Kakao.isInitialized() && KAKAO_JS_KEY) {
    try {
      window.Kakao.init(KAKAO_JS_KEY)
    } catch (e) {
      console.warn('Failed to initialize Kakao JS SDK:', e)
      return false
    }
  }

  return !!window.Kakao.isInitialized()
}

/**
 * Reports user-initiated share attempt to the Flask backend without claiming delivery.
 */
async function reportShareAttemptSafely(messageId: string, channel: string): Promise<void> {
  try {
    await api.reportShareAttempt(messageId, { channel })
  } catch (err) {
    // Non-fatal telemetry: do not interrupt user share experience
    console.warn('Backend share initiation report notice:', err)
  }
}

/**
 * Initiates user-directed KakaoTalk sharing.
 *
 * CRITICAL ARCHITECTURAL BOUNDARY:
 * 1. Moatok NEVER automatically posts to KakaoTalk chat rooms or Open Chats.
 * 2. Clicking 'Share to KakaoTalk' triggers the official SDK or system picker,
 *    allowing the user to choose the destination.
 * 3. Clicking the button DOES NOT mark the message as delivered; delivery is decoupled.
 * 4. Open Chat room selection availability must be checked on a real device with KakaoTalk installed.
 * 5. Private KakaoTalk protocols (kakaotalk:// internal RPCs) and background UI automation
 *    are strictly forbidden.
 * 6. The shared link points to the registered domain detail page, which contains the original article link.
 */
export async function initiateKakaoShare(message: ShareMessage): Promise<ShareResult> {
  const shareText = message.body || message.title
  const registeredUrl = getRegisteredMessageUrl(message.id)
  const openChatNotice =
    '오픈채팅방 공유 및 전송 가능 여부는 카카오톡 앱이 설치된 실제 모바일 기기(iOS/Android)에서 확인해야 합니다.'

  // 1. Attempt Kakao JavaScript SDK Share (Default Feed/Text template)
  if (typeof window !== 'undefined' && !window.Kakao) {
    await loadKakaoSdkScript()
  }

  const isKakaoReady = initKakaoSdk()
  if (isKakaoReady && window.Kakao?.Share?.sendDefault) {
    const receiptId = beginKakaoDelivery(message.id)
    try {
      const payload = message.kakao_share_payload
      if (payload && payload.template_type === 'feed' && payload.image_url) {
        window.Kakao.Share.sendDefault({
          objectType: 'feed',
          serverCallbackArgs: { receipt_id: receiptId },
          content: {
            title: message.title,
            description: payload.description || message.body.slice(0, 100),
            imageUrl: payload.image_url,
            link: {
              mobileWebUrl: registeredUrl,
              webUrl: registeredUrl
            }
          },
          buttons: [
            {
              title: payload.button_title || '브리핑 상세 보기',
              link: {
                mobileWebUrl: registeredUrl,
                webUrl: registeredUrl
              }
            }
          ]
        })
      } else {
        window.Kakao.Share.sendDefault({
          objectType: 'text',
          serverCallbackArgs: { receipt_id: receiptId },
          text: shareText,
          link: {
            mobileWebUrl: registeredUrl,
            webUrl: registeredUrl
          },
          buttonTitle: '브리핑 상세 보기'
        })
      }

      await reportShareAttemptSafely(message.id, 'kakao_sdk')

      return {
        success: true,
        channel: 'kakao_sdk',
        notice: '카카오톡 공유 창이 열렸습니다. 전송할 대상 채팅방을 직접 선택해주세요.',
        detailUrl: registeredUrl,
        openChatNotice
      }
    } catch (err) {
      forgetKakaoDelivery(receiptId)
      console.warn('Kakao SDK share failed, attempting Web Share fallback:', err)
    }
  }

  // 2. Fallback: Web Share API (Mobile OS Share Sheet -> User selects KakaoTalk)
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      await navigator.share({
        title: message.title,
        text: shareText,
        url: registeredUrl
      })

      await reportShareAttemptSafely(message.id, 'web_share')

      return {
        success: true,
        channel: 'web_share',
        notice: '시스템 공유 창이 열렸습니다. 카카오톡 및 대상 채팅방을 직접 선택해주세요.',
        detailUrl: registeredUrl,
        openChatNotice
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return {
          success: false,
          channel: 'web_share',
          notice: '공유가 취소되었습니다.',
          detailUrl: registeredUrl,
          openChatNotice
        }
      }
      console.warn('Web Share failed, attempting clipboard fallback:', err)
    }
  }

  // 3. Fallback: Copy formatted text to clipboard and prompt user to paste in KakaoTalk
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(shareText)

      await reportShareAttemptSafely(message.id, 'clipboard')

      return {
        success: true,
        channel: 'clipboard',
        notice:
          '브리핑 내용이 클립보드에 복사되었습니다. 카카오톡을 열고 원하는 채팅방에 붙여넣어 공유하세요.',
        detailUrl: registeredUrl,
        openChatNotice
      }
    } catch (copyErr) {
      console.error('Clipboard copy failed:', copyErr)
    }
  }

  return {
    success: false,
    channel: 'clipboard',
    notice: '자동 공유를 시작할 수 없습니다. 내용을 수동으로 복사하여 카카오톡에 공유하세요.',
    detailUrl: registeredUrl,
    openChatNotice
  }
}
