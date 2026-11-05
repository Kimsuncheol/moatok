import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'
import * as firebaseAuth from 'firebase/auth'

vi.mock('@/services/firebase', () => ({
  getFirebaseAuth: vi.fn(() => ({})),
  getFirebaseApp: vi.fn(() => ({}))
}))

vi.mock('firebase/auth', async () => {
  const actual = await vi.importActual<typeof import('firebase/auth')>('firebase/auth')
  return {
    ...actual,
    signInAnonymously: vi.fn(),
    signInWithEmailAndPassword: vi.fn(),
    createUserWithEmailAndPassword: vi.fn(),
    signInWithPopup: vi.fn(),
    signInWithCustomToken: vi.fn(),
    signOut: vi.fn(),
    onAuthStateChanged: vi.fn(),
    onIdTokenChanged: vi.fn(),
    GoogleAuthProvider: vi.fn()
  }
})

describe('Pinia Auth Store (useAuthStore)', () => {
  let authCallbacks: ((user: any) => void)[] = []

  beforeEach(() => {
    setActivePinia(createPinia())
    authCallbacks = []
    vi.restoreAllMocks()

    vi.mocked(firebaseAuth.onAuthStateChanged).mockImplementation((auth, callback: any) => {
      authCallbacks.push(callback)
      return vi.fn()
    })

    vi.mocked(firebaseAuth.onIdTokenChanged).mockImplementation(() => {
      return vi.fn()
    })

    vi.spyOn(api, 'getProfile').mockResolvedValue({
      user: {
        uid: 'user_test_123',
        email: 'test@example.com',
        role: 'admin',
        is_admin: true
      }
    })
  })

  it('starts with loading state and transitions to signed_out when auth listener yields null', async () => {
    const store = useAuthStore()
    expect(store.status).toBe('loading')
    expect(store.isAuthenticated).toBe(false)

    store.init()
    expect(authCallbacks.length).toBeGreaterThan(0)

    // Simulate Firebase reporting no user signed in
    await authCallbacks[0](null)

    expect(store.status).toBe('signed_out')
    expect(store.isSignedOut).toBe(true)
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(store.profile).toBeNull()
  })

  it('authenticates user and syncs profile claims when auth listener yields user', async () => {
    const store = useAuthStore()
    store.init()

    const mockFirebaseUser = {
      uid: 'user_test_123',
      email: 'test@example.com',
      getIdToken: vi.fn().mockResolvedValue('token-abc')
    }

    await authCallbacks[0](mockFirebaseUser)

    expect(store.status).toBe('authenticated')
    expect(store.isAuthenticated).toBe(true)
    expect(store.isAdmin).toBe(true)
    expect(store.userEmail).toBe('test@example.com')
    expect(store.userUid).toBe('user_test_123')
    expect(api.getProfile).toHaveBeenCalledTimes(1)
  })

  it('successfully logs in with email and password', async () => {
    const store = useAuthStore()
    const mockUser = {
      uid: 'user_456',
      email: 'admin@example.com',
      getIdToken: vi.fn().mockResolvedValue('token-456')
    }

    vi.mocked(firebaseAuth.signInWithEmailAndPassword).mockResolvedValue({
      user: mockUser
    } as any)

    const result = await store.loginWithEmail('admin@example.com', 'password123')
    expect(result).toBe(mockUser)
    expect(store.status).toBe('authenticated')
    expect(store.isAuthenticated).toBe(true)
    expect(store.error).toBeNull()
    expect(firebaseAuth.signInWithEmailAndPassword).toHaveBeenCalledWith(
      expect.anything(),
      'admin@example.com',
      'password123'
    )
  })

  it('maps Firebase auth errors to friendly localized messages on email login failure', async () => {
    const store = useAuthStore()

    const authError: any = new Error('Invalid credentials')
    authError.code = 'auth/invalid-credential'
    vi.mocked(firebaseAuth.signInWithEmailAndPassword).mockRejectedValue(authError)

    await expect(
      store.loginWithEmail('wrong@example.com', 'badpass')
    ).rejects.toThrow()

    expect(store.status).toBe('error')
    expect(store.error).toBe('이메일 또는 비밀번호가 올바르지 않습니다.')
    expect(store.isAuthenticated).toBe(false)
  })

  it('successfully creates an account via signupWithEmail', async () => {
    const store = useAuthStore()
    const mockUser = {
      uid: 'new_user_789',
      email: 'new@example.com',
      getIdToken: vi.fn().mockResolvedValue('token-789')
    }

    vi.mocked(firebaseAuth.createUserWithEmailAndPassword).mockResolvedValue({
      user: mockUser
    } as any)

    const result = await store.signupWithEmail('new@example.com', 'password123')
    expect(result).toBe(mockUser)
    expect(store.status).toBe('authenticated')
    expect(firebaseAuth.createUserWithEmailAndPassword).toHaveBeenCalledWith(
      expect.anything(),
      'new@example.com',
      'password123'
    )
  })

  it('signs in anonymously via loginAsGuest', async () => {
    const store = useAuthStore()
    const mockGuestUser = {
      uid: 'anon_user_999',
      email: null,
      getIdToken: vi.fn().mockResolvedValue('token-anon')
    }

    vi.mocked(firebaseAuth.signInAnonymously).mockResolvedValue({
      user: mockGuestUser
    } as any)

    await store.loginAsGuest()
    expect(store.status).toBe('authenticated')
    expect(store.isAuthenticated).toBe(true)
    expect(firebaseAuth.signInAnonymously).toHaveBeenCalled()
  })

  it('supports configurable polymorphic signIn method', async () => {
    const store = useAuthStore()

    const mockGuest = { uid: 'guest_poly', getIdToken: vi.fn().mockResolvedValue('t1') }
    vi.mocked(firebaseAuth.signInAnonymously).mockResolvedValue({ user: mockGuest } as any)

    const mockEmailUser = { uid: 'email_poly', getIdToken: vi.fn().mockResolvedValue('t2') }
    vi.mocked(firebaseAuth.signInWithEmailAndPassword).mockResolvedValue({ user: mockEmailUser } as any)

    // 1. Anonymous method
    await store.signIn({ method: 'anonymous' })
    expect(firebaseAuth.signInAnonymously).toHaveBeenCalled()

    // 2. Email method
    await store.signIn({
      method: 'email',
      email: 'hello@example.com',
      password: 'mypassword'
    })
    expect(firebaseAuth.signInWithEmailAndPassword).toHaveBeenCalledWith(
      expect.anything(),
      'hello@example.com',
      'mypassword'
    )
  })

  it('passes forceRefresh parameter to user.getIdToken', async () => {
    const store = useAuthStore()
    const getIdTokenSpy = vi.fn().mockResolvedValue('forced-refreshed-token')
    store.user = {
      getIdToken: getIdTokenSpy
    } as any

    const token = await store.getIdToken(true)
    expect(token).toBe('forced-refreshed-token')
    expect(getIdTokenSpy).toHaveBeenCalledWith(true)
  })

  it('handles session expiration appropriately', () => {
    const store = useAuthStore()
    store.user = { uid: 'u1' } as any
    store.profile = { uid: 'u1', email: 'u1@example.com', role: 'user', is_admin: false }
    store.status = 'authenticated'

    store.handleSessionExpired()

    expect(store.sessionExpired).toBe(true)
    expect(store.status).toBe('expired')
    expect(store.user).toBeNull()
    expect(store.profile).toBeNull()
    expect(store.error).toBe('세션이 만료되었습니다. 다시 로그인해주세요.')
  })

  it('signs out and resets state cleanly on logout', async () => {
    const store = useAuthStore()
    store.user = { uid: 'u1' } as any
    store.profile = { uid: 'u1', email: 'u1@example.com', role: 'user', is_admin: false }
    store.status = 'authenticated'

    vi.mocked(firebaseAuth.signOut).mockResolvedValue(undefined)

    await store.logout()

    expect(store.status).toBe('signed_out')
    expect(store.isSignedOut).toBe(true)
    expect(store.user).toBeNull()
    expect(store.profile).toBeNull()
    expect(store.sessionExpired).toBe(false)
    expect(firebaseAuth.signOut).toHaveBeenCalledTimes(1)
  })

  it('clears error and restores state on clearError', () => {
    const store = useAuthStore()
    store.error = 'Something went wrong'
    store.status = 'error'

    store.clearError()

    expect(store.error).toBeNull()
    expect(store.status).toBe('signed_out')
  })
})
