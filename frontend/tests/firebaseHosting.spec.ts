import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('Firebase Hosting & SPA Configuration', () => {
  const rootDir = path.resolve(__dirname, '../../')
  const firebaseJsonPath = path.join(rootDir, 'firebase.json')
  const firebasercPath = path.join(rootDir, '.firebaserc')

  it('provides a valid firebase.json pointing to frontend/dist with SPA fallback', () => {
    expect(fs.existsSync(firebaseJsonPath)).toBe(true)

    const raw = fs.readFileSync(firebaseJsonPath, 'utf-8')
    const config = JSON.parse(raw)

    expect(config.hosting).toBeDefined()
    expect(config.hosting.public).toBe('frontend/dist')

    // SPA fallback verification
    const rewrites = config.hosting.rewrites
    expect(Array.isArray(rewrites)).toBe(true)
    const spaRewrite = rewrites.find((r: any) => r.source === '**' && r.destination === '/index.html')
    expect(spaRewrite).toBeDefined()

    // Service Worker & Manifest caching header verification
    const headers = config.hosting.headers
    expect(Array.isArray(headers)).toBe(true)

    const swHeader = headers.find((h: any) => h.source === '/sw.js')
    expect(swHeader).toBeDefined()
    const swCacheControl = swHeader.headers.find((kv: any) => kv.key === 'Cache-Control')
    expect(swCacheControl.value).toContain('no-cache')

    const manifestHeader = headers.find((h: any) => h.source === '/manifest.webmanifest')
    expect(manifestHeader).toBeDefined()
    const manifestContentType = manifestHeader.headers.find((kv: any) => kv.key === 'Content-Type')
    expect(manifestContentType.value).toContain('application/manifest+json')
  })

  it('provides .firebaserc for project alias configuration', () => {
    expect(fs.existsSync(firebasercPath)).toBe(true)
    const raw = fs.readFileSync(firebasercPath, 'utf-8')
    const rc = JSON.parse(raw)
    expect(rc.projects).toBeDefined()
    expect(rc.projects.default).toBeDefined()
  })
})
