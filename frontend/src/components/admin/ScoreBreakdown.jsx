import React from 'react'

/**
 * Renders component score progress bars (0–100).
 */

const SCORE_LABELS = [
  { key: 'skill_match', label: 'Skill Match', color: 'bg-emerald-500' },
  { key: 'location', label: 'Location', color: 'bg-blue-500' },
  { key: 'availability', label: 'Availability', color: 'bg-indigo-500' },
  { key: 'rating', label: 'Rating', color: 'bg-amber-500' },
  { key: 'experience', label: 'Experience', color: 'bg-purple-500' },
  { key: 'workload_fairness', label: 'Fairness', color: 'bg-teal-500' },
]

export default function ScoreBreakdown({ breakdown }) {
  if (!breakdown) return null

  return (
    <div className="space-y-2 text-xs">
      {SCORE_LABELS.map(({ key, label, color }) => {
        const val = Math.round(breakdown[key] || 0)
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="w-24 font-medium text-slate-600 shrink-0">{label}</span>
            <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full ${color} transition-all duration-500 rounded-full`}
                style={{ width: `${val}%` }}
              />
            </div>
            <span className="w-8 text-right font-semibold text-slate-700 shrink-0">{val}</span>
          </div>
        )
      })}
    </div>
  )
}
