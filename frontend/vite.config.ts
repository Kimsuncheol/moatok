import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: [
        'favicon.svg',
        'favicon.png',
        'apple-touch-icon.png',
        'pwa-192x192.png',
        'pwa-512x512.png',
        'icon-192.svg',
        'icon-512.svg'
      ],
      manifest: {
        name: 'Moatok · 카카오톡 공유 비서',
        short_name: 'Moatok',
        description: '수집된 브리핑을 검토하고 사용자가 직접 카카오톡 대상 채팅방으로 공유하는 모바일 비서 PWA',
        theme_color: '#000000',
        background_color: '#000000',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        categories: ['news', 'productivity', 'utilities'],
        icons: [
          {
            src: '/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: '/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: '/icon-192.svg',
            sizes: '192x192',
            type: 'image/svg+xml',
            purpose: 'any'
          },
          {
            src: '/icon-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'any'
          }
        ]
      },
      workbox: {
        // Safe App Shell caching: precache static HTML, JS, CSS, fonts, and icons
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],
        cleanupOutdatedCaches: true,
        navigateFallback: '/index.html',
        // Critical: Do NOT fall back for API, health, or internal scheduler endpoints
        navigateFallbackDenylist: [/^\/api\//, /^\/health/, /^\/internal\//],
        runtimeCaching: [
          {
            // CRITICAL: Never cache authenticated API endpoints or sensitive user data
            urlPattern: /^\/api\/.*/,
            handler: 'NetworkOnly'
          },
          {
            urlPattern: /^\/health$/,
            handler: 'NetworkOnly'
          },
          {
            urlPattern: /^\/internal\/.*/,
            handler: 'NetworkOnly'
          }
        ]
      }
    })
  ],
  css: {
    postcss: {}
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
