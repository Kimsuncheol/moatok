import type { ShareMessage } from '@/types'

export interface ShareResult {
  success: boolean
  channel: 'kakao_sdk' | 'web_share' | 'clipboard'
  notice: string
}

const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY || ''

export function initKakaoSdk(): boolean {
  if (typeof window === 'undefined') return false
  if (!window.Kakao) {
    return false
  }

  if (!window.Kakao.isInitialized() && KAKAO_JS_KEY) {
    try {
      window.Kakao.init(KAKAO_JS_KEY)
    } catch (e) {
      console.warn('Failed to initialize Kakao JS SDK:', e)
      return false
    }
  }

  return window.Kakao.isInitialized()
}

/**
 * Initiates user-directed KakaoTalk sharing.
 *
 * CRITICAL ARCHITECTURAL BOUNDARY:
 * Moatok NEVER automatically posts to KakaoTalk chat rooms or Open Chats.
 * Instead, this helper launches the official Kakao Share picker, system Web Share sheet,
 * or copies the structured message to the clipboard so the user explicitly chooses
 * the target destination in KakaoTalk.
 */
export async function initiateKakaoShare(message: ShareMessage): Promise<ShareResult> {
  const shareText = message.body || message.title
  const targetUrl = message.target_url || (typeof window !== 'undefined' ? window.location.href : '')

  // 1. Attempt Kakao JavaScript SDK Share (Default Feed/Text template)
  const isKakaoReady = initKakaoSdk()
  if (isKakaoReady && window.Kakao) {
    try {
      const payload = message.kakao_share_payload
      if (payload && payload.template_type === 'feed' && payload.image_url) {
        window.Kakao.Share.sendDefault({
          objectType: 'feed',
          content: {
            title: message.title,
            description: payload.description || message.body.slice(0, 100),
            imageUrl: payload.image_url,
            link: {
              mobileWebUrl: targetUrl,
              webUrl: targetUrl
            }
          },
          buttons: [
            {
              title: payload.button_title || '자세히 보기',
              link: {
                mobileWebUrl: targetUrl,
                webUrl: targetUrl
              }
            }
          ]
        })
      } else {
        window.Kakao.Share.sendDefault({
          objectType: 'text',
          text: shareText,
          link: {
            mobileWebUrl: targetUrl,
            webUrl: targetUrl
          },
          buttonTitle: '원문 링크 확인'
        })
      }

      return {
        success: true,
        channel: 'kakao_sdk',
        notice: '카카오톡 공유 창이 열렸습니다. 전송할 대상 채팅방을 직접 선택해주세요.'
      }
    } catch (err) {
      console.warn('Kakao SDK share failed, trying Web Share fallback:', err)
    }
  }

  // 2. Attempt Web Share API (Mobile OS Share Sheet -> User selects KakaoTalk)
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      await navigator.share({
        title: message.title,
        text: shareText,
        url: targetUrl || undefined
      })
      return {
        success: true,
        channel: 'web_share',
        notice: '공유 창에서 카카오톡 및 대상 채팅방을 직접 선택해주세요.'
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User cancelled share sheet
        return {
          success: false,
          channel: 'web_share',
          notice: '공유가 취소되었습니다.'
        }
      }
      console.warn('Web Share failed, falling back to clipboard copy:', err)
    }
  }

  // 3. Fallback: Copy formatted text to clipboard and prompt user to paste in KakaoTalk
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(shareText)
      return {
        success: true,
        channel: 'clipboard',
        notice: '브리핑 내용이 클립보드에 복사되었습니다. 카카오톡을 열고 원하는 채팅방에 붙여넣어 공유하세요.'
      }
    } catch (copyErr) {
      console.error('Clipboard copy failed:', copyErr)
    }
  }

  return {
    success: false,
    channel: 'clipboard',
    notice: '자동 공유를 시작할 수 없습니다. 내용을 수동으로 복사하여 카카오톡에 공유하세요.'
  }
}
