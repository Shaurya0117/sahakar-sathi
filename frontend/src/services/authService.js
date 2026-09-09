/**
 * Authentication API calls.
 *
 * All auth-related HTTP calls go through here.
 * Never call axios/api directly from components.
 *
 * NOTE: Login uses URLSearchParams (application/x-www-form-urlencoded)
 * because the backend uses OAuth2PasswordRequestForm.
 */
import api from './api'

/**
 * Register a new customer or worker.
 * @param {{ name, email, phone, password, role }} data
 */
export const register = (data) =>
  api.post('/auth/register', data)

/**
 * Login and obtain a JWT.
 * FastAPI OAuth2PasswordRequestForm expects form-encoded body.
 * @param {string} email
 * @param {string} password
 */
export const login = (email, password) => {
  const params = new URLSearchParams()
  params.append('username', email)   // OAuth2 field name is "username"
  params.append('password', password)
  return api.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

/**
 * Get current user profile. Requires a valid JWT in the request header.
 */
export const getMe = () => api.get('/auth/me')
