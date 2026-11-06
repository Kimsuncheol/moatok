import type { EnglishLesson } from './api'

const base = (import.meta.env.VITE_ENGLISH_SCRAPER_URL || 'https://english-scrapper.onrender.com').replace(/\/+$/, '')
const core = ['expression', 'korean_meaning', 'korean_explanation', 'english_dialogue', 'korean_dialogue_translation']

export async function fetchEnglishLesson({ url }: { url: string }) {
  let parsed: URL
  try { parsed = new URL(url) } catch { throw new Error('올바른 기사 URL을 입력하세요.') }
  if (parsed.protocol !== 'https:' || !['chosun.com', 'www.chosun.com'].includes(parsed.hostname) || parsed.username || parsed.password || (parsed.port && parsed.port !== '443')) {
    throw new Error('조선일보 HTTPS 기사 URL을 입력하세요.')
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 120_000)
  try {
    const response = await fetch(base + '/api/v1/lessons/fetch', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_url: parsed.href }),
      signal: controller.signal, credentials: 'omit'
    })
    let data: any
    try { data = await response.json() } catch { throw new Error('영어 수업 서버에서 올바른 응답을 받지 못했습니다.') }
    if (!response.ok) throw new Error(data.error?.message || '영어 수업을 가져오지 못했습니다.')
    const payload = data
    if (!payload) throw new Error('이 목록에서 가져올 영어 수업을 찾지 못했습니다.')
    const rawFields = payload.lesson?.fields
    if (!rawFields || !payload.article?.url) throw new Error('영어 수업 응답에 필수 정보가 없습니다.')
    const fields: Record<string, string> = {}
    for (const [key, value] of Object.entries(rawFields)) {
      const text = (value as { text?: unknown } | null)?.text
      if (typeof text === 'string' && text.trim()) fields[key] = text.trim()
    }
    const missing = core.filter(key => !fields[key] || fields[key].toLowerCase().includes('[unreadable]'))
    const ocr = payload.ocr
    if (!ocr?.raw_text?.trim()) missing.push('transcript')
    if (ocr?.status !== 'ok') missing.push('ocr_quality')
    const lesson: EnglishLesson = { url: payload.article.url, fields, missing_sections: missing }
    return { status: missing.length ? 'held' : 'fetched', lesson }
  } catch (error) {
    if (controller.signal.aborted) throw new Error('수업 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.')
    if (error instanceof TypeError) throw new Error('영어 수업 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    throw error
  } finally { clearTimeout(timer) }
}
