import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { getApiUrl } from '@/lib/config'
import { authApi, type SignupData, type LoginData } from '@/lib/api/auth'
import type { User } from '@/lib/types/auth'

interface AuthState {
  isAuthenticated: boolean
  token: string | null
  user: User | null
  isLoading: boolean
  error: string | null
  lastAuthCheck: number | null
  isCheckingAuth: boolean
  hasHydrated: boolean
  authRequired: boolean | null
  setHasHydrated: (state: boolean) => void
  checkAuthRequired: () => Promise<boolean>
  login: (credentials: LoginData) => Promise<boolean>
  signup: (credentials: SignupData) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      token: null,
      user: null,
      isLoading: false,
      error: null,
      lastAuthCheck: null,
      isCheckingAuth: false,
      hasHydrated: false,
      authRequired: null,

      setHasHydrated: (state: boolean) => {
        set({ hasHydrated: state })
      },

      checkAuthRequired: async () => {
        try {
          const data = await authApi.checkAuthStatus()
          const required = data.auth_enabled || false
          set({ authRequired: required })

          // If auth is not required, mark as authenticated
          if (!required) {
            set({ isAuthenticated: true, token: 'not-required' })
          }

          return required
        } catch (error) {
          console.error('Failed to check auth status:', error)

          // If it's a network error, set a more helpful error message
          if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            set({
              error: 'Unable to connect to server. Please check if the API is running.',
              authRequired: null
            })
          } else {
            // For other errors, default to requiring auth to be safe
            set({ authRequired: true })
          }

          throw error
        }
      },

      signup: async (credentials: SignupData) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.signup(credentials)
          
          set({ 
            isAuthenticated: true, 
            token: response.access_token,
            user: response.user,
            isLoading: false,
            lastAuthCheck: Date.now(),
            error: null
          })
          return true
        } catch (error: any) {
          console.error('Signup error:', error)
          let errorMessage = 'Signup failed'
          
          if (error.response?.data?.detail) {
            if (typeof error.response.data.detail === 'string') {
              errorMessage = error.response.data.detail
            } else if (Array.isArray(error.response.data.detail)) {
              errorMessage = error.response.data.detail.map((e: any) => e.msg).join(', ')
            }
          } else if (error.response?.status === 400) {
            errorMessage = 'Invalid signup data. Please check your inputs.'
          } else if (error.response?.status >= 500) {
            errorMessage = 'Server error. Please try again later.'
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ 
            error: errorMessage,
            isLoading: false,
            isAuthenticated: false,
            token: null,
            user: null
          })
          return false
        }
      },

      login: async (credentials: LoginData) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.login(credentials)
          
          set({ 
            isAuthenticated: true, 
            token: response.access_token,
            user: response.user,
            isLoading: false,
            lastAuthCheck: Date.now(),
            error: null
          })
          return true
        } catch (error: any) {
          console.error('Login error:', error)
          let errorMessage = 'Login failed'
          
          if (error.response?.data?.detail) {
            if (typeof error.response.data.detail === 'string') {
              errorMessage = error.response.data.detail
            } else if (Array.isArray(error.response.data.detail)) {
              errorMessage = error.response.data.detail.map((e: any) => e.msg).join(', ')
            }
          } else if (error.response?.status === 401) {
            errorMessage = 'Invalid username or password'
          } else if (error.response?.status === 403) {
            errorMessage = 'Account is disabled'
          } else if (error.response?.status >= 500) {
            errorMessage = 'Server error. Please try again later.'
          } else if (error.message) {
            errorMessage = error.message
          }
          
          set({ 
            error: errorMessage,
            isLoading: false,
            isAuthenticated: false,
            token: null,
            user: null
          })
          return false
        }
      },
      
      logout: () => {
        set({ 
          isAuthenticated: false, 
          token: null,
          user: null,
          error: null 
        })
      },
      
      checkAuth: async () => {
        const state = get()
        const { token, lastAuthCheck, isCheckingAuth, isAuthenticated } = state

        // If already checking, return current auth state
        if (isCheckingAuth) {
          return isAuthenticated
        }

        // If no token, not authenticated
        if (!token) {
          return false
        }

        // If we checked recently (within 30 seconds) and are authenticated, skip
        const now = Date.now()
        if (isAuthenticated && lastAuthCheck && (now - lastAuthCheck) < 30000) {
          return true
        }

        set({ isCheckingAuth: true })

        try {
          const apiUrl = await getApiUrl()

          const response = await fetch(`${apiUrl}/api/notebooks`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (response.ok) {
            set({ 
              isAuthenticated: true, 
              lastAuthCheck: now,
              isCheckingAuth: false 
            })
            return true
          } else {
            set({
              isAuthenticated: false,
              token: null,
              user: null,
              lastAuthCheck: null,
              isCheckingAuth: false
            })
            return false
          }
        } catch (error) {
          console.error('checkAuth error:', error)
          set({ 
            isAuthenticated: false, 
            token: null,
            user: null,
            lastAuthCheck: null,
            isCheckingAuth: false 
          })
          return false
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)