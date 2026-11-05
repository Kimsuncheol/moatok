import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('PWA Web App Manifest and Icon Assets', () => {
  const publicDir = path.resolve(__dirname, '../public')
  const manifestPath = path.join(publicDir, 'manifest.webmanifest')

  it('contains a valid web app manifest with standalone display and theme colors', () => {
    expect(fs.existsSync(manifestPath)).toBe(true)
    const raw = fs.readFileSync(manifestPath, 'utf8')
    const manifest = JSON.parse(raw)

    expect(manifest.name).toBeTruthy()
    expect(manifest.short_name).toBeTruthy()
    expect(manifest.display).toBe('standalone')
    expect(manifest.theme_color).toBe('#000000')
    expect(manifest.background_color).toBe('#000000')
    expect(Array.isArray(manifest.icons)).toBe(true)
  })

  it('includes 192px and 512px icons that exist on disk', () => {
    const raw = fs.readFileSync(manifestPath, 'utf8')
    const manifest = JSON.parse(raw)

    const sizes = manifest.icons.map((i: any) => i.sizes)
    expect(sizes).toContain('192x192')
    expect(sizes).toContain('512x512')

    // Verify local image files exist
    expect(fs.existsSync(path.join(publicDir, 'pwa-192x192.png'))).toBe(true)
    expect(fs.existsSync(path.join(publicDir, 'pwa-512x512.png'))).toBe(true)
    expect(fs.existsSync(path.join(publicDir, 'icon-192.svg'))).toBe(true)
    expect(fs.existsSync(path.join(publicDir, 'icon-512.svg'))).toBe(true)
    expect(fs.existsSync(path.join(publicDir, 'apple-touch-icon.png'))).toBe(true)
  })
})
