import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'https://argonut-backend-production.up.railway.app'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// --- Request interceptor: adjunta access token ---
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- Response interceptor: intenta refresh en 401 ---
let isRefreshing = false
let queue: Array<(token: string) => void> = []

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        clearAuth()
        return Promise.reject(error)
      }
      if (isRefreshing) {
        return new Promise((resolve) => {
          queue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`
            resolve(api(original))
          })
        })
      }
      isRefreshing = true
      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newToken = data.access_token
        localStorage.setItem('access_token', newToken)
        queue.forEach((cb) => cb(newToken))
        queue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        clearAuth()
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export function clearAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}
