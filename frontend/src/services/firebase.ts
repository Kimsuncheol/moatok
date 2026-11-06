import { initializeApp, getApps, type FirebaseApp } from 'firebase/app'
import { getAuth, type Auth } from 'firebase/auth'
import { getMessaging, type Messaging, isSupported } from 'firebase/messaging'

// Public Firebase web identifiers for this app; build variables can override them.
// Keep these defaults usable when Hosting builds have no local .env file.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyCsaoNaudfMiBxNFynYsyTf6rMNqS1FaxM',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'moatalk-e6fe1.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'moatalk-e6fe1',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'moatalk-e6fe1.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '523175594353',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:523175594353:web:b373cb781f5546dcaf0ed0'
}

let app: FirebaseApp | null = null
let auth: Auth | null = null
let messaging: Messaging | null = null

export function getFirebaseApp(): FirebaseApp {
  if (!app) {
    app = getApps().length > 0 ? getApps()[0] : initializeApp(firebaseConfig)
  }
  return app
}

export function getFirebaseAuth(): Auth {
  if (!auth) {
    auth = getAuth(getFirebaseApp())
  }
  return auth
}

export async function getFirebaseMessaging(): Promise<Messaging | null> {
  if (typeof window === 'undefined') return null
  try {
    const supported = await isSupported()
    if (!supported) return null
    if (!messaging) {
      messaging = getMessaging(getFirebaseApp())
    }
    return messaging
  } catch (err) {
    console.warn('Firebase Messaging not supported in this environment:', err)
    return null
  }
}
