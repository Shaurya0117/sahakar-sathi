/**
 * Customer Service Requests API calls.
 */
import api from './api'

/**
 * Create a new service request (CUSTOMER only).
 * @param {{ service_id, location, preferred_date, preferred_time, description }} data
 */
export const createServiceRequest = (data) => api.post('/requests', data)

/**
 * Get all service requests owned by the authenticated customer.
 */
export const getMyServiceRequests = () => api.get('/requests/me')

/**
 * Get details of a single request owned by the authenticated customer.
 * @param {number} requestId
 */
export const getServiceRequestById = (requestId) => api.get(`/requests/${requestId}`)

/**
 * Cancel a pending request.
 * @param {number} requestId
 */
export const cancelServiceRequest = (requestId) => api.patch(`/requests/${requestId}/cancel`)

/**
 * Get all cooperative service requests (ADMIN only).
 */
export const getCooperativeServiceRequests = () => api.get('/requests')

/**
 * Upload a photo for a service request.
 * @param {number} requestId
 * @param {File} file
 */
export const uploadServiceRequestPhoto = (requestId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/requests/${requestId}/upload-photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
