import { getApiBaseUrl } from './api'

const KEY = 'moatok_kakao_delivery_receipts_v1'
interface Receipt { id: string; messageId: string; expires: number }
let memory: Receipt[] = []
function read(): Receipt[] {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '[]')
    if (Array.isArray(saved)) memory = [...memory, ...saved]
  } catch { /* Keep session receipts if storage is unavailable. */ }
  memory = [...new Map(memory.filter(r => /^[a-f0-9]{64}$/.test(r.id) && typeof r.messageId === 'string' && r.expires > Date.now()).map(r => [r.id, r])).values()].slice(-100)
  return memory
}
function save(receipts: Receipt[]) {
  memory = receipts
  try { localStorage.setItem(KEY, JSON.stringify(receipts)) } catch { /* Session only. */ }
}
export function beginKakaoDelivery(messageId: string): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32))
  const id = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
  save([...read(), { id, messageId, expires: Date.now() + 86_400_000 }].slice(-100))
  return id
}
export function forgetKakaoDelivery(id: string) { save(read().filter(r => r.id !== id)) }

// Only the authenticated server webhook can produce a delivered response.
export async function checkKakaoDeliveries(confirm: (messageId: string) => Promise<boolean>) {
  for (const receipt of read()) {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/kakao/share/receipts/${receipt.id}`, {
        credentials: 'omit', cache: 'no-store', signal: AbortSignal.timeout(8000)
      })
      if (!response.ok) continue
      const data = await response.json()
      if (data.delivered === true && await confirm(receipt.messageId)) forgetKakaoDelivery(receipt.id)
    } catch { /* Keep receipts for the next foreground check; never infer success. */ }
  }
}
