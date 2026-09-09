/**
 * AuthContext — global authentication state.
 *
 * Provides:
 *   user          — current user object or null
 *   token         — JWT string or null
 *   isAuthenticated — boolean
 *   loading       — true while restoring session from localStorage
 *   login(email, password) → Promise  — authenticates and stores token
 *   logout()               — clears all auth state
 *
 * Token storage: localStorage (acceptable for hackathon prototype).
 * Production note: prefer secure HttpOnly cookies backed by a refresh-token
 * flow to mitigate XSS token theft.
 */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { login as apiLogin, getMe } from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  // ── Restore session from localStorage on first mount ─────────────────────
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token')
    const storedUser  = localStorage.getItem('auth_user')

    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
      } catch {
        // Corrupt storage — clear it
        localStorage.removeItem('access_token')
        localStorage.removeItem('auth_user')
      }
    }
    setLoading(false)
  }, [])

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const res = await apiLogin(email, password)
    const { access_token, user: userData } = res.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('auth_user', JSON.stringify(userData))

    setToken(access_token)
    setUser(userData)

    return userData  // caller can inspect role for routing
  }, [])

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('auth_user')
    setToken(null)
    setUser(null)
  }, [])

  const value = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    loading,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Convenience hook — throws if used outside AuthProvider. */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
