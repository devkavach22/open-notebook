export interface AuthState {
  isAuthenticated: boolean
  token: string | null
  user: User | null
  isLoading: boolean
  error: string | null
}

export interface User {
  id: string
  username: string
  email: string
  created_at: string
  is_active: boolean
  last_login: string | null
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface SignupCredentials {
  username: string
  email: string
  password: string
}