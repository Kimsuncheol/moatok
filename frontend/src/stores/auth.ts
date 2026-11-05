import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  signInAnonymously,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  type User
} from 'firebase/auth'
import { getFirebaseAuth } from '@/services/firebase'
import { setTokenProvider, api } from '@/services/api'
import type { UserProfile } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const profile = ref<UserProfile | null>(null)
  const loading = ref<boolean>(true)
  const error = ref<string | null>(null)
  const isInitialized = ref<boolean>(false)

  // Register token provider with API client
  setTokenProvider(async () => {
    return getIdToken()
  })

  async function getIdToken(forceRefresh = false): Promise<string | null> {
    if (user.value) {
      try {
        return await user.value.getIdToken(forceRefresh)
      } catch (e) {
        console.warn('Failed to retrieve Firebase ID token:', e)
      }
    }
    // Fallback for local demo/testing mode without live Firebase project
    if (typeof window !== 'undefined') {
      const demoToken = localStorage.getItem('moatok_demo_token')
      if (demoToken) return demoToken
    }
    return null
  }

  function init() {
    if (isInitialized.value) return
    isInitialized.value = true

    try {
      const auth = getFirebaseAuth()
      onAuthStateChanged(auth, async (currentUser) => {
        user.value = currentUser
        loading.value = false
        if (currentUser) {
          try {
            const res = await api.getProfile()
            profile.value = res.user
          } catch {
            profile.value = {
              uid: currentUser.uid,
              email: currentUser.email,
              role: 'user',
              is_admin: false
            }
          }
        } else {
          profile.value = null
        }
      })
    } catch (err: any) {
      console.warn('Firebase Auth initialization skipped (using mock/offline auth):', err)
      loading.value = false
    }
  }

  async function loginAsGuest() {
    error.value = null
    try {
      const auth = getFirebaseAuth()
      const cred = await signInAnonymously(auth)
      user.value = cred.user
      profile.value = {
        uid: cred.user.uid,
        email: null,
        role: 'user',
        is_admin: false
      }
    } catch (err: any) {
      // Local fallback mock
      const mockUid = `demo-guest-${Date.now().toString(36)}`
      if (typeof window !== 'undefined') {
        localStorage.setItem('moatok_demo_token', `demo-token-${mockUid}`)
      }
      profile.value = {
        uid: mockUid,
        email: null,
        role: 'user',
        is_admin: false
      }
      error.value = null
    }
  }

  async function loginWithEmail(email: string, pass: string) {
    error.value = null
    try {
      const auth = getFirebaseAuth()
      const cred = await signInWithEmailAndPassword(auth, email, pass)
      user.value = cred.user
    } catch (err: any) {
      error.value = err.message || '로그인에 실패했습니다.'
      throw err
    }
  }

  async function signupWithEmail(email: string, pass: string) {
    error.value = null
    try {
      const auth = getFirebaseAuth()
      const cred = await createUserWithEmailAndPassword(auth, email, pass)
      user.value = cred.user
    } catch (err: any) {
      error.value = err.message || '회원가입에 실패했습니다.'
      throw err
    }
  }

  async function logout() {
    try {
      const auth = getFirebaseAuth()
      await signOut(auth)
    } catch {
      // ignore
    }
    user.value = null
    profile.value = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('moatok_demo_token')
    }
  }

  return {
    user,
    profile,
    loading,
    error,
    isInitialized,
    init,
    getIdToken,
    loginAsGuest,
    loginWithEmail,
    signupWithEmail,
    logout
  }
})
