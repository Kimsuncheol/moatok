/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />
/// <reference types="vite-plugin-pwa/vue" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface Window {
  Kakao?: {
    init: (appKey: string) => void
    isInitialized: () => boolean
    Auth?: { setAccessToken: (token: string, persist?: boolean) => void }
    API?: { request: (options: any) => Promise<{result_code: number}> }
    Share: {
      sendDefault: (options: any) => void
      sendCustom: (options: any) => void
    }
  }
}
