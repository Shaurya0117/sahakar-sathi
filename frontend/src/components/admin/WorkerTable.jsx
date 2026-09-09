/**
 * WorkerTable — renders workforce list with status badges, profile completion, and Action inspect button.
 */
export default function WorkerTable({ workers, onSelectWorker }) {
  if (workers.length === 0) {
    return (
      <div className="glass-card p-12 text-center text-slate-400">
        <div className="text-4xl mb-3">🔍</div>
        <p className="font-semibold text-slate-300">No workers match your filter criteria.</p>
        <p className="text-xs text-slate-500 mt-1">Try clearing search terms or status filters.</p>
      </div>
    )
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-white/5 text-xs uppercase font-semibold text-slate-400 border-b border-white/10">
            <tr>
              <th className="px-6 py-4">Worker</th>
              <th className="px-6 py-4">Profession</th>
              <th className="px-6 py-4">Experience</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Availability</th>
              <th className="px-6 py-4">Rating</th>
              <th className="px-6 py-4">Verification</th>
              <th className="px-6 py-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {workers.map((worker) => (
              <tr key={worker.id} className="hover:bg-white/3 transition-colors">
                {/* Worker Name & Email */}
                <td className="px-6 py-4">
                  <div>
                    <p className="font-semibold text-slate-100">{worker.name}</p>
                    <p className="text-xs text-slate-400">{worker.email}</p>
                  </div>
                </td>

                {/* Profession */}
                <td className="px-6 py-4">
                  <span className="font-medium text-slate-200">
                    {worker.profession || 'Unspecified'}
                  </span>
                </td>

                {/* Experience */}
                <td className="px-6 py-4 text-slate-400">
                  {worker.experience_years != null ? `${worker.experience_years} yrs` : 'N/A'}
                </td>

                {/* Location */}
                <td className="px-6 py-4 text-slate-400 max-w-[160px] truncate">
                  📍 {worker.location || 'Not set'}
                </td>

                {/* Availability */}
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      worker.availability === 'AVAILABLE'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        worker.availability === 'AVAILABLE' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                      }`}
                    />
                    {worker.availability}
                  </span>
                </td>

                {/* Rating */}
                <td className="px-6 py-4 text-amber-400 font-medium">
                  {worker.rating > 0 ? `${worker.rating.toFixed(1)} ★` : '—'}
                </td>

                {/* Verification */}
                <td className="px-6 py-4">
                  <StatusBadge status={worker.verification_status} />
                </td>

                {/* Action */}
                <td className="px-6 py-4 text-right">
                  <button
                    id={`inspect-worker-${worker.id}`}
                    onClick={() => onSelectWorker(worker)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-primary-300 bg-primary-500/10 hover:bg-primary-500/20 border border-primary-500/30 transition-all"
                  >
                    Inspect →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  switch (status) {
    case 'VERIFIED':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          ✓ Verified
        </span>
      )
    case 'REJECTED':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          ✕ Rejected
        </span>
      )
    case 'PENDING':
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          ⏳ Pending
        </span>
      )
  }
}
