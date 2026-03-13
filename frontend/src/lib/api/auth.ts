import apiClient from './client'

export interface SignupData {
  username: string
  email: string
  password: string
}

export interface LoginData {
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    username: string
    email: string
    created_at: string
    is_active: boolean
    last_login: string | null
  }
}

export interface ForgotPasswordData {
  email: string
}

export interface ForgotPasswordResponse {
  message: string
  reset_token?: string  // Only in development
  expires_in_minutes?: number
}

export interface ResetPasswordData {
  token: string
  new_password: string
}

export interface ResetPasswordResponse {
  message: string
}

export const authApi = {
  signup: async (data: SignupData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/signup', data)
    return response.data
  },

  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/auth/login', data)
    return response.data
  },

  checkAuthStatus: async (): Promise<{ auth_enabled: boolean }> => {
    const response = await apiClient.get<{ auth_enabled: boolean }>('/auth/status')
    return response.data
  },

  forgotPassword: async (data: ForgotPasswordData): Promise<ForgotPasswordResponse> => {
    const response = await apiClient.post<ForgotPasswordResponse>('/auth/forgot-password', data)
    return response.data
  },

  resetPassword: async (data: ResetPasswordData): Promise<ResetPasswordResponse> => {
    const response = await apiClient.post<ResetPasswordResponse>('/auth/reset-password', data)
    return response.data
  }
}
