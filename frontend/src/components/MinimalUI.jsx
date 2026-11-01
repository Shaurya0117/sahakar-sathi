// Minimalist shared UI components for Sahakar Sathi dashboards
// Pill Tab Bar, Stat Row, Job Timeline Card, Circular Progress, Empty State

// ─── PillTabBar ───────────────────────────────────────────────
export function PillTabBar({ tabs, activeTab, onChange }) {
  return (
    <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-2xl w-fit mx-auto">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
            activeTab === tab.id
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>{tab.icon}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )
}

// ─── StatRow ──────────────────────────────────────────────────
export function StatRow({ stats }) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {stats.map((s, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <span className="text-lg">{s.icon}</span>
          <div>
            <div className="text-xs font-bold text-slate-900 leading-none">{s.value}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{s.label}</div>
          </div>
          {i < stats.length - 1 && (
            <div className="w-px h-6 bg-slate-200 ml-3" />
          )}
        </div>
      ))}
    </div>
  )
}

// ─── CircularProgress ─────────────────────────────────────────
export function CircularProgress({ value, max = 100, size = 80, label, sublabel }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const r = (size - 10) / 2
  const circ = 2 * Math.PI * r
  const dash = circ - (pct / 100) * circ
  const color = pct >= 80 ? '#ef4444' : pct >= 60 ? '#f59e0b' : '#10b981'

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
          <circle
            cx={size/2} cy={size/2} r={r} fill="none"
            stroke={color} strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={dash}
            style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-extrabold text-slate-900">{Math.round(pct)}%</span>
        </div>
      </div>
      {label && <div className="text-xs font-semibold text-slate-700 text-center">{label}</div>}
      {sublabel && <div className="text-[10px] text-slate-400 text-center">{sublabel}</div>}
    </div>
  )
}

// ─── JobTimelineCard ──────────────────────────────────────────
const STATUS_META = {
  ASSIGNED:    { color: 'bg-amber-400',   bg: 'bg-amber-50',   text: 'text-amber-800',   border: 'border-amber-200',  label: '⏳ Awaiting Response' },
  ACCEPTED:    { color: 'bg-blue-400',    bg: 'bg-blue-50',    text: 'text-blue-800',    border: 'border-blue-200',   label: '✓ Accepted' },
  IN_PROGRESS: { color: 'bg-indigo-500',  bg: 'bg-indigo-50',  text: 'text-indigo-800',  border: 'border-indigo-200', label: '🔧 In Progress' },
  COMPLETED:   { color: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200',label: '✅ Completed' },
}

export function JobTimelineCard({ job, expanded, onToggle, children }) {
  const meta = STATUS_META[job.status] || { color: 'bg-slate-300', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', label: job.status }

  return (
    <div className="flex gap-3">
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-1.5 shrink-0">
        <div className={`w-3 h-3 rounded-full ${meta.color} ring-4 ring-white shadow-sm`} />
        <div className="w-px flex-1 bg-slate-200 mt-1" />
      </div>

      {/* Card */}
      <div className="flex-1 mb-4">
        <button
          onClick={onToggle}
          className="w-full text-left bg-white border border-slate-200 rounded-2xl p-4 hover:border-slate-300 hover:shadow-sm transition-all"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-slate-900">{job.service_name}</h4>
              <p className="text-xs text-slate-500 mt-0.5">
                {job.customer_name} · {job.scheduled_date}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${meta.bg} ${meta.text} border ${meta.border}`}>
                {meta.label}
              </span>
              <span className="text-slate-400 text-xs">{expanded ? '▲' : '▼'}</span>
            </div>
          </div>
        </button>

        {/* Expanded details */}
        {expanded && (
          <div className="mt-1.5 bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-3">
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── EmptyState ───────────────────────────────────────────────
export function EmptyState({ icon = '📭', title, message, actionLabel, onAction }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center gap-3">
      <div className="text-4xl">{icon}</div>
      <div>
        <p className="text-sm font-bold text-slate-700">{title}</p>
        {message && <p className="text-xs text-slate-400 mt-1 max-w-xs">{message}</p>}
      </div>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

// ─── MinimalCard ──────────────────────────────────────────────
export function MinimalCard({ children, className = '' }) {
  return (
    <div className={`bg-white border border-slate-200 rounded-2xl shadow-xs ${className}`}>
      {children}
    </div>
  )
}

// ─── SectionHeader ────────────────────────────────────────────
export function SectionHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h2 className="text-base font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

// ─── StatusPill ───────────────────────────────────────────────
export function StatusPill({ status }) {
  const meta = STATUS_META[status] || { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', label: status }
  return (
    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${meta.bg} ${meta.text} ${meta.border}`}>
      {meta.label}
    </span>
  )
}
