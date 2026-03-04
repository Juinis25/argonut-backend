import { api, setTokens, clearAuth } from './client'
import type { User, AuthTokens } from '@/types'

export const authApi = {
  async login(email: string, password: string): Promise<AuthTokens> {
    const { data } = await api.post<AuthTokens>('/auth/login', { email, password })
    setTokens(data.access_token, data.refresh_token)
    return data
  },

  async register(email: string, password: string, nombre: string): Promise<User> {
    const { data } = await api.post<User>('/auth/register', { email, password, nombre })
    return data
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>('/auth/me')
    return data
  },

  logout() {
    clearAuth()
  },
}
