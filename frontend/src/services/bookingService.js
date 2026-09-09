/**
 * Worker Allocation & Booking Workflow API calls.
 */
import api from './api'

/**
 * Allocate a worker to a service request (ADMIN only).
 * @param {number} requestId
 * @param {number} workerId
 * @param {number|null} amount
 */
export const allocateWorker = (requestId, workerId, amount = null) =>
  api.post(`/requests/${requestId}/allocate`, { worker_id: workerId, amount })

/**
 * Get all assigned jobs for the authenticated worker.
 */
export const getWorkerJobs = () => api.get('/bookings/worker')

/**
 * Get all bookings for the authenticated customer.
 */
export const getCustomerBookings = () => api.get('/bookings/me')

/**
 * Get all cooperative bookings (ADMIN only).
 */
export const getCooperativeBookings = () => api.get('/bookings')

/**
 * Get details of a single booking.
 * @param {number} bookingId
 */
export const getBookingById = (bookingId) => api.get(`/bookings/${bookingId}`)

/**
 * Worker accepts an assigned job.
 * @param {number} bookingId
 */
export const acceptJob = (bookingId) => api.patch(`/bookings/${bookingId}/accept`)

/**
 * Worker rejects an assigned job.
 * @param {number} bookingId
 */
export const rejectJob = (bookingId) => api.patch(`/bookings/${bookingId}/reject`)

/**
 * Worker starts an accepted service.
 * @param {number} bookingId
 */
export const startJob = (bookingId) => api.patch(`/bookings/${bookingId}/start`)

/**
 * Worker marks a service completed.
 * @param {number} bookingId
 */
export const completeJob = (bookingId, payload = null) => api.patch(`/bookings/${bookingId}/complete`, payload)

/**
 * Customer reviews a completed job.
 * @param {number} bookingId
 * @param {number} rating 1-5
 * @param {string} review optional review text
 */
export const submitReview = (bookingId, rating, review) => 
  api.post(`/bookings/${bookingId}/review`, { rating, review })
