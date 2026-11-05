/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface Window {
  Kakao?: {
    init: (appKey: string) => void
    isInitialized: () => boolean
    Share: {
      sendDefault: (options: any) => void
      sendCustom: (options: any) => void
    }
  }
}
