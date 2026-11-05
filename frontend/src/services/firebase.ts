import { initializeApp, getApps, type FirebaseApp } from 'firebase/app'
import { getAuth, type Auth } from 'firebase/auth'
import { getMessaging, type Messaging, isSupported } from 'firebase/messaging'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'demo-api-key',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'demo-moatok.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'demo-moatok',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'demo-moatok.appspot.com',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '1234567890',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:1234567890:web:demoapp'
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
