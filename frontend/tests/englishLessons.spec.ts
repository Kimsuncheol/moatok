import { describe, it, expect, vi, afterEach } from 'vitest'
import { fetchEnglishLesson } from '@/services/englishLessons'

const payload = { article: { url: 'https://www.chosun.com/national/nie/english/2026/11/06/example/' }, lesson: { fields: Object.fromEntries(['expression', 'korean_meaning', 'korean_explanation', 'english_dialogue', 'korean_dialogue_translation'].map(key => [key, { text: 'Hello\nWorld' }])) }, ocr: { raw_text: 'Hello', status: 'ok' } }
afterEach(() => vi.unstubAllGlobals())
describe('Public English API connection', () => {
  it('routes section URLs to the production series endpoint without credentials', async () => {
    const mock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)))
    vi.stubGlobal('fetch', mock)
    const result = await fetchEnglishLesson({ url: 'https://www.chosun.com/national/nie/english/' })
    expect(mock).toHaveBeenCalledWith('https://english-scrapper.onrender.com/api/v1/lessons/fetch', expect.objectContaining({ method: 'POST', credentials: 'omit' }))
    expect(result.status).toBe('fetched')
    expect(result.lesson.fields.english_dialogue).toBe('Hello\nWorld')
  })
  it('posts individual articles to scrape and holds incomplete results', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...payload, ocr: { status: 'low_confidence' } }))))
    const result = await fetchEnglishLesson({ url: payload.article.url })
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/lessons/fetch'), expect.objectContaining({ body: JSON.stringify({ article_url: payload.article.url }) }))
    expect(result.status).toBe('held')
  })
  it('rejects unsupported URLs before any network request', async () => {
    vi.stubGlobal('fetch', vi.fn())
    await expect(fetchEnglishLesson({ url: 'https://localhost/test' })).rejects.toThrow('HTTPS')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('handles empty series, upstream errors, and HTML responses', async () => {
    const mock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(null)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: 'OCR busy' } }), { status: 503 }))
      .mockResolvedValueOnce(new Response('<html>'))
    vi.stubGlobal('fetch', mock)
    const input = { url: 'https://www.chosun.com/national/nie/english/' }
    await expect(fetchEnglishLesson(input)).rejects.toThrow('찾지 못했습니다')
    await expect(fetchEnglishLesson(input)).rejects.toThrow('OCR busy')
    await expect(fetchEnglishLesson(input)).rejects.toThrow('올바른 응답')
  })
})
