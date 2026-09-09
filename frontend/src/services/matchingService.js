/**
 * Explainable Cooperative Worker Matching API calls.
 */
import api from './api'

/**
 * Fetch ranked worker recommendations for a service request (ADMIN only).
 * @param {number} requestId
 */
export const getMatchingRecommendations = (requestId) => api.get(`/matching/requests/${requestId}`)
