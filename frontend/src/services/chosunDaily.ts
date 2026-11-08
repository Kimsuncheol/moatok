import { getApiBaseUrl } from './api'

export const CHOSUN_ARTICLES_URL = 'https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10'

export function isChosunDaily(url: string): boolean {
  return url === CHOSUN_ARTICLES_URL
}

export async function fetchChosunArticles() {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/integrations/chosun-daily/articles`, {
    credentials: 'omit', signal: AbortSignal.timeout(90_000)
  })
  if (!response.ok) throw new Error(`조선일보 기사 수집 실패 (HTTP ${response.status})`)
  const data = await response.json()
  if (!Array.isArray(data.items)) throw new Error('올바른 기사 목록을 받지 못했습니다.')
  return data.items.map((article: any) => {
    if (!Number.isInteger(article.id) || typeof article.title !== 'string' ||
        typeof article.url !== 'string' || !article.url.startsWith('https://www.chosun.com/')) {
      throw new Error('기사 필수 정보가 올바르지 않습니다.')
    }
    return { id: article.id as number, title: article.title as string, url: article.url as string,
      body: typeof article.body === 'string' ? article.body : (article.description || '본문이 제공되지 않은 기사입니다.') }
  }) as { id: number; title: string; url: string; body: string }[]
}
