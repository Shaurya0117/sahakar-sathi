/**
 * Worker profile API calls.
 *
 * All worker-related HTTP requests go through here.
 * Components and pages must not call axios directly.
 */
import api from './api'

/**
 * Get the authenticated worker's own profile.
 * Returns 404 if no profile exists yet.
 */
export const getMyWorkerProfile = () => api.get('/workers/me')

/**
 * Create the authenticated worker's profile.
 * @param {Object} data - WorkerCreateRequest payload
 */
export const createWorkerProfile = (data) => api.post('/workers/me', data)

/**
 * Update the authenticated worker's profile.
 * Send only the fields you want to change.
 * @param {Object} data - WorkerUpdateRequest payload (partial)
 */
export const updateWorkerProfile = (data) => api.put('/workers/me', data)

/**
 * Get any worker's profile by ID.
 * @param {number} workerId
 */
export const getWorkerById = (workerId) => api.get(`/workers/${workerId}`)

/**
 * List all worker profiles (ADMIN only).
 */
export const listAllWorkers = () => api.get('/workers')

/**
 * Update a worker's verification status (ADMIN only).
 * @param {number} workerId
 * @param {'PENDING'|'VERIFIED'|'REJECTED'} status
 */
export const updateVerificationStatus = (workerId, status) =>
  api.patch(`/workers/${workerId}/verification`, { status })
