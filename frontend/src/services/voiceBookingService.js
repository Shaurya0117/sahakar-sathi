/**
 * Voice Booking API Service — Sahakar Sathi.
 * Wraps backend endpoints for the VoiceBookingBot component.
 */
import api from './api'

/**
 * Submit a voice-captured booking intent to the backend.
 * Backend matches a worker and sends Hindi SMS.
 *
 * @param {{ service_type, urgency, location, latitude, longitude, description }} data
 */
export const submitVoiceBooking = (data) =>
  api.post('/api/voice-booking', data)

/**
 * Trigger fallback — reassign booking to next worker after decline.
 *
 * @param {number} bookingId
 * @param {string} reason
 */
export const fallbackVoiceBooking = (bookingId, reason = 'Worker declined') =>
  api.post('/api/voice-booking/fallback', { booking_id: bookingId, reason })

/**
 * Poll the status of a voice booking.
 *
 * @param {number} bookingId
 */
export const getVoiceBookingStatus = (bookingId) =>
  api.get(`/api/voice-booking/${bookingId}/status`)

/**
 * Demo only: simulate a worker SMS reply.
 * reply = "1" (accept) or "2" (decline)
 *
 * @param {number} bookingId
 * @param {"1"|"2"} reply
 */
export const simulateSmsReply = (bookingId, reply) =>
  api.post('/api/sms/simulate-reply', { booking_id: bookingId, reply })
