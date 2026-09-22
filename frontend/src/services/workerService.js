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

/**
 * Patent Feature: Peer Verification
 * Get pending verification candidates for peer review.
 */
export const getPeerVerificationCandidates = () => api.get('/peer-verification/candidates')

/**
 * Patent Feature: Peer Verification
 * Submit a verification vote for a pending candidate.
 */
export const submitPeerVote = (candidateId, isPositive) =>
  api.post('/peer-verification/vote', { candidate_id: candidateId, is_positive: isPositive })

// ── Cooperative Micro-Credit ────────────────────────────────────────────────

/** Check loan eligibility based on trust score tier. */
export const getMicroCreditEligibility = () => api.get('/microcredit/eligibility')

/** Apply for a micro-loan from the cooperative fund. */
export const applyMicroLoan = (amount, purpose = 'Salary Advance') =>
  api.post('/microcredit/apply', { amount, purpose })

/** Get all of the worker's loans. */
export const getMyLoans = () => api.get('/microcredit/my-loans')

// ── Cooperative Governance ──────────────────────────────────────────────────

/** List all cooperative proposals. */
export const getGovernanceProposals = () => api.get('/governance/proposals')

/** Cast a vote on a proposal. */
export const voteOnProposal = (proposalId, vote) =>
  api.post(`/governance/proposals/${proposalId}/vote`, { vote })

