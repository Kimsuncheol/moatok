import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  signInAnonymously,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signInWithCustomToken,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  onIdTokenChanged,
  type User
} from 'firebase/auth'
import { getFirebaseAuth } from '@/services/firebase'
import { setTokenProvider, setOnSessionExpired, api, ApiError } from '@/services/api'
import type {
  UserProfile,
  AuthSignInMethod,
  AuthStatus,
  SignInCredentials
} from '@/types'

function formatAuthError(err: any): string {
  if (!err) return '인증 오류가 발생했습니다.'
  const code = err.code || ''
  switch (code) {
    case 'auth/invalid-credential':
      return '이메일 또는 비밀번호가 올바르지 않습니다.'
    case 'auth/user-not-found':
      return '가입되지 않은 이메일입니다.'
    case 'auth/wrong-password':
      return '비밀번호가 일치하지 않습니다.'
    case 'auth/email-already-in-use':
      return '이미 가입된 이메일 주소입니다.'
    case 'auth/weak-password':
      return '비밀번호는 최소 6자 이상이어야 합니다.'
    case 'auth/invalid-email':
      return '유효한 이메일 형식을 입력해주세요.'
    case 'auth/user-disabled':
      return '관리자에 의해 비활성화된 계정입니다.'
    case 'auth/too-many-requests':
      return '너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해주세요.'
    case 'auth/popup-closed-by-user':
      return '로그인 팝업이 사용자에 의해 닫혔습니다.'
    case 'auth/network-request-failed':
      return '네트워크 연결이 원활하지 않습니다.'
    default:
      return err.message || '인증 처리에 실패했습니다.'
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const profile = ref<UserProfile | null>(null)
  const status = ref<AuthStatus>('loading')
  const loading = ref<boolean>(true)
  const error = ref<string | null>(null)
  const sessionExpired = ref<boolean>(false)
  const isInitialized = ref<boolean>(false)

  // Configurable sign-in method from environment (default: 'email')
  const configuredMethod = (
    (import.meta.env.VITE_FIREBASE_AUTH_SIGN_IN_METHOD as string | undefined)?.toLowerCase() ||
    'email'
  ) as AuthSignInMethod
  const preferredSignInMethod = ref<AuthSignInMethod>(configuredMethod)

  // Computed getters
  const isAuthenticated = computed(
    () => status.value === 'authenticated' && !!user.value
  )
  const isSignedOut = computed(() => status.value === 'signed_out')
  const isLoading = computed(() => loading.value || status.value === 'loading')
  const isAdmin = computed(
    () => profile.value?.is_admin === true || profile.value?.role === 'admin'
  )
  const currentUser = computed(() => user.value)
  const userEmail = computed(() => user.value?.email || profile.value?.email || null)
  const userUid = computed(() => user.value?.uid || profile.value?.uid || null)

  // Register token provider and session expiration listener with API client
  setTokenProvider(async (forceRefresh = false) => {
    return getIdToken(forceRefresh)
  })

  setOnSessionExpired((apiError) => {
    handleSessionExpired(apiError)
  })

  async function getIdToken(forceRefresh = false): Promise<string | null> {
    if (user.value) {
      try {
        return await user.value.getIdToken(forceRefresh)
      } catch (e) {
        console.warn('Failed to retrieve Firebase ID token:', e)
      }
    }
    // Fallback for local testing / mock mode
    if (typeof window !== 'undefined') {
      try {
        const demoToken = localStorage.getItem('moatok_demo_token')
        if (demoToken) return demoToken
      } catch {
        // LocalStorage might be restricted in some test environments
      }
    }
    return null
  }

  function handleSessionExpired(_apiErr?: ApiError) {
    sessionExpired.value = true
    status.value = 'expired'
    error.value = '세션이 만료되었습니다. 다시 로그인해주세요.'
    user.value = null
    profile.value = null
  }

  async function syncProfile(currentUser: User): Promise<UserProfile> {
    try {
      const res = await api.getProfile()
      profile.value = res.user
      return res.user
    } catch {
      // Fallback profile if offline or mock backend
      const fallback: UserProfile = {
        uid: currentUser.uid,
        email: currentUser.email,
        role: 'user',
        is_admin: false
      }
      profile.value = fallback
      return fallback
    }
  }

  function init() {
    if (isInitialized.value) return
    isInitialized.value = true
    loading.value = true
    status.value = 'loading'

    try {
      const auth = getFirebaseAuth()

      onAuthStateChanged(auth, async (currentUser) => {
        if (currentUser) {
          user.value = currentUser
          sessionExpired.value = false
          await syncProfile(currentUser)
          status.value = 'authenticated'
        } else {
          user.value = null
          profile.value = null
          if (status.value !== 'expired') {
            status.value = 'signed_out'
          }
        }
        loading.value = false
      })

      // Proactively listen for token changes to keep auth state fresh
      onIdTokenChanged(auth, async (currentUser) => {
        if (currentUser) {
          user.value = currentUser
          if (status.value === 'expired') {
            sessionExpired.value = false
            status.value = 'authenticated'
          }
        }
      })
    } catch (err: any) {
      console.warn('Firebase Auth initialization skipped (using mock/offline auth):', err)
      loading.value = false
      status.value = 'signed_out'
    }
  }

  // Configurable polymorphic sign-in method
  async function signIn(credentials?: SignInCredentials): Promise<User | null> {
    const method = credentials?.method || preferredSignInMethod.value || 'email'
    switch (method) {
      case 'anonymous':
        return loginAsGuest()
      case 'google':
        return loginWithGoogle()
      case 'custom':
        if (!credentials?.token) {
          throw new Error('Custom token is required for custom token authentication.')
        }
        return loginWithCustomToken(credentials.token)
      case 'email':
      default:
        if (!credentials?.email || !credentials?.password) {
          throw new Error('이메일과 비밀번호를 입력해주세요.')
        }
        return loginWithEmail(credentials.email, credentials.password)
    }
  }

  async function loginWithEmail(email: string, pass: string): Promise<User> {
    loading.value = true
    error.value = null
    sessionExpired.value = false
    try {
      const auth = getFirebaseAuth()
      const cred = await signInWithEmailAndPassword(auth, email, pass)
      user.value = cred.user
      await syncProfile(cred.user)
      status.value = 'authenticated'
      return cred.user
    } catch (err: any) {
      error.value = formatAuthError(err)
      status.value = 'error'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function signupWithEmail(email: string, pass: string): Promise<User> {
    loading.value = true
    error.value = null
    sessionExpired.value = false
    try {
      const auth = getFirebaseAuth()
      const cred = await createUserWithEmailAndPassword(auth, email, pass)
      user.value = cred.user
      await syncProfile(cred.user)
      status.value = 'authenticated'
      return cred.user
    } catch (err: any) {
      error.value = formatAuthError(err)
      status.value = 'error'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loginAsGuest(): Promise<User | null> {
    loading.value = true
    error.value = null
    sessionExpired.value = false
    try {
      const auth = getFirebaseAuth()
      const cred = await signInAnonymously(auth)
      user.value = cred.user
      await syncProfile(cred.user)
      status.value = 'authenticated'
      return cred.user
    } catch (err: any) {
      // Local fallback mock if Firebase Auth is not active locally
      const mockUid = `guest-${Date.now().toString(36)}`
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem('moatok_demo_token', `demo-token-${mockUid}`)
        } catch {
          // ignore
        }
      }
      profile.value = {
        uid: mockUid,
        email: null,
        role: 'user',
        is_admin: false
      }
      status.value = 'authenticated'
      return null
    } finally {
      loading.value = false
    }
  }

  async function loginWithGoogle(): Promise<User> {
    loading.value = true
    error.value = null
    sessionExpired.value = false
    try {
      const auth = getFirebaseAuth()
      const provider = new GoogleAuthProvider()
      const cred = await signInWithPopup(auth, provider)
      user.value = cred.user
      await syncProfile(cred.user)
      status.value = 'authenticated'
      return cred.user
    } catch (err: any) {
      error.value = formatAuthError(err)
      status.value = 'error'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loginWithCustomToken(customToken: string): Promise<User> {
    loading.value = true
    error.value = null
    sessionExpired.value = false
    try {
      const auth = getFirebaseAuth()
      const cred = await signInWithCustomToken(auth, customToken)
      user.value = cred.user
      await syncProfile(cred.user)
      status.value = 'authenticated'
      return cred.user
    } catch (err: any) {
      error.value = formatAuthError(err)
      status.value = 'error'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function refreshSession(): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const token = await getIdToken(true)
      if (token && user.value) {
        await syncProfile(user.value)
        sessionExpired.value = false
        status.value = 'authenticated'
        return true
      }
      return false
    } catch (err: any) {
      error.value = '세션 갱신에 실패했습니다. 다시 로그인해주세요.'
      handleSessionExpired()
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      const auth = getFirebaseAuth()
      await signOut(auth)
    } catch {
      // ignore
    }
    user.value = null
    profile.value = null
    error.value = null
    sessionExpired.value = false
    status.value = 'signed_out'
    loading.value = false
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('moatok_demo_token')
      } catch {
        // ignore
      }
    }
  }

  function clearError() {
    error.value = null
    if (status.value === 'error') {
      status.value = user.value ? 'authenticated' : 'signed_out'
    }
  }

  function setPreferredSignInMethod(method: AuthSignInMethod) {
    preferredSignInMethod.value = method
  }

  return {
    user,
    profile,
    status,
    loading,
    error,
    sessionExpired,
    isInitialized,
    preferredSignInMethod,

    // Getters
    isAuthenticated,
    isSignedOut,
    isLoading,
    isAdmin,
    currentUser,
    userEmail,
    userUid,

    // Actions
    init,
    getIdToken,
    signIn,
    loginWithEmail,
    signupWithEmail,
    loginAsGuest,
    loginWithGoogle,
    loginWithCustomToken,
    refreshSession,
    handleSessionExpired,
    logout,
    clearError,
    setPreferredSignInMethod
  }
})
