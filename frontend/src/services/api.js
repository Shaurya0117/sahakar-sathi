/**
 * API service layer.
 *
 * All HTTP calls to the backend go through this file.
 * Components must never call fetch/axios directly.
 */
import axios from 'axios'

const api = axios.create({
  // During development, Vite proxies /api → http://localhost:8000
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// ── Request interceptor — attach JWT token when available ──────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor — handle global errors ────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear local storage
      localStorage.removeItem('access_token')
    }
    return Promise.reject(error)
  }
)

// ── Health ─────────────────────────────────────────────────────────────────
export const checkHealth = () => api.get('/health')

export default api
