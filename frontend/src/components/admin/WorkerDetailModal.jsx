/**
 * WorkerDetailModal — inspect worker details & perform admin verification actions.
 *
 * Actions:
 * - Verify Worker (status -> VERIFIED)
 * - Reject Worker (status -> REJECTED)
 * - Reset to Pending (status -> PENDING)
 */
import { useState } from 'react'

export default function WorkerDetailModal({ worker, onClose, onVerifyStatusChange }) {
  const [updating, setUpdating] = useState(false)

  if (!worker) return null

  const handleStatusChange = async (newStatus) => {
    setUpdating(true)
    try {
      await onVerifyStatusChange(worker.id, newStatus)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="glass-card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 space-y-6 relative border-primary-500/30">

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary-500/20 border border-primary-500/30 flex items-center justify-center text-3xl">
            🔧
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-100">{worker.name}</h2>
            <p className="text-sm text-slate-400">{worker.email} • {worker.phone || 'No phone provided'}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300">
                Worker ID #{worker.id}
              </span>
              <StatusBadge status={worker.verification_status} />
            </div>
          </div>
        </div>

        {/* Profile Completion Bar */}
        <div className="bg-white/3 p-4 rounded-xl border border-white/5">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="font-semibold text-slate-300">Profile Completion</span>
            <span className="font-bold text-primary-400">{worker.profile_completion}%</span>
          </div>
          <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary-600 to-accent-400"
              style={{ width: `${worker.profile_completion}%` }}
            />
          </div>
        </div>

        {/* Detail Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/3 p-4 rounded-xl border border-white/5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Profession</p>
            <p className="text-base font-bold text-slate-100">{worker.profession || 'Not set'}</p>
          </div>

          <div className="bg-white/3 p-4 rounded-xl border border-white/5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Experience</p>
            <p className="text-base font-bold text-slate-100">{worker.experience_years} Years</p>
          </div>

          <div className="bg-white/3 p-4 rounded-xl border border-white/5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Location</p>
            <p className="text-base font-bold text-slate-100">📍 {worker.location || 'Not set'}</p>
          </div>

          <div className="bg-white/3 p-4 rounded-xl border border-white/5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Availability</p>
            <p className={`text-base font-bold ${worker.availability === 'AVAILABLE' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {worker.availability}
            </p>
            {worker.availability_description && (
              <p className="text-xs text-slate-400 mt-0.5">{worker.availability_description}</p>
            )}
          </div>
        </div>

        {/* Skills Tag List */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Registered Skills</p>
          <div className="flex flex-wrap gap-2">
            {worker.skills && worker.skills.length > 0 ? (
              worker.skills.map((s) => (
                <span
                  key={s}
                  className="px-3 py-1 rounded-lg text-xs font-medium bg-primary-500/10 text-primary-300 border border-primary-500/20"
                >
                  ✓ {s}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500 italic">No skills specified</span>
            )}
          </div>
        </div>

        {/* Rating & Job Performance */}
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div className="bg-white/3 p-3 rounded-xl border border-white/5">
            <p className="text-xs text-slate-400">Cooperative Rating</p>
            <p className="text-lg font-bold text-amber-400 mt-0.5">
              {worker.rating > 0 ? `${worker.rating.toFixed(1)} ★` : 'No rating'}
            </p>
          </div>
          <div className="bg-white/3 p-3 rounded-xl border border-white/5">
            <p className="text-xs text-slate-400">Total Completed Jobs</p>
            <p className="text-lg font-bold text-slate-100 mt-0.5">{worker.total_jobs}</p>
          </div>
        </div>

        {/* ── Admin Verification Actions ─────────────────────────────────── */}
        <div className="pt-4 border-t border-white/10">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Cooperative Verification Action
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              id="admin-verify-btn"
              type="button"
              disabled={updating || worker.verification_status === 'VERIFIED'}
              onClick={() => handleStatusChange('VERIFIED')}
              className="flex-1 py-2.5 px-4 rounded-xl font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 transition-all text-sm flex items-center justify-center gap-2"
            >
              ✓ Verify Worker
            </button>

            <button
              id="admin-reject-btn"
              type="button"
              disabled={updating || worker.verification_status === 'REJECTED'}
              onClick={() => handleStatusChange('REJECTED')}
              className="flex-1 py-2.5 px-4 rounded-xl font-semibold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-40 transition-all text-sm flex items-center justify-center gap-2"
            >
              ✕ Reject Worker
            </button>

            <button
              id="admin-reset-btn"
              type="button"
              disabled={updating || worker.verification_status === 'PENDING'}
              onClick={() => handleStatusChange('PENDING')}
              className="py-2.5 px-4 rounded-xl font-medium text-slate-300 bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-40 transition-all text-sm"
            >
              Set to Pending
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  switch (status) {
    case 'VERIFIED':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          Verified
        </span>
      )
    case 'REJECTED':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          Rejected
        </span>
      )
    case 'PENDING':
    default:
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          Pending Verification
        </span>
      )
  }
}
