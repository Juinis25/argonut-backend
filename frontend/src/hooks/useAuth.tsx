import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import type { User } from '@/types'
import { authApi } from '@/api/auth'
import { clearAuth } from '@/api/client'

export interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, nombre: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}

export function useAuthState(): AuthContextType {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { setLoading(false); return }
    authApi.me()
      .then(setUser)
      .catch(() => clearAuth())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authApi.login(email, password)
    const me = await authApi.me()
    setUser(me)
  }, [])

  const register = useCallback(async (email: string, password: string, nombre: string) => {
    await authApi.register(email, password, nombre)
    await login(email, password)
  }, [login])

  const logout = useCallback(() => {
    authApi.logout()
    setUser(null)
  }, [])

  return { user, loading, login, register, logout }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const value = useAuthState()
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
