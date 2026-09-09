/**
 * Cooperative & Admin API calls.
 */
import api from './api'

/**
 * Get primary cooperative information (ADMIN only).
 */
export const getCooperativeInfo = () => api.get('/cooperative/me')

/**
 * Get live cooperative statistics (ADMIN only).
 */
export const getCooperativeStats = () => api.get('/cooperative/stats')

/**
 * Get active services catalog.
 */
export const getServices = () => api.get('/services')

/**
 * Get cooperative analytics (ADMIN only).
 */
export const getCooperativeAnalytics = () => api.get('/cooperative/analytics')
