import React from 'react'
import ScoreBreakdown from './ScoreBreakdown'

export default function RecommendationCard({ rank, recommendation, onAllocate, allocating = false }) {
  const {
    worker_id,
    worker_name,
    profession,
    verification_status,
    rating,
    experience_years,
    location,
    total_jobs,
    score,
    breakdown,
    reasons,
  } = recommendation

  const isTopRank = rank === 1

  return (
    <div
      className={`relative rounded-xl border p-5 transition-all ${
        isTopRank
          ? 'border-emerald-300 bg-gradient-to-br from-emerald-50/40 via-white to-white shadow-md'
          : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      {/* Top Banner & Rank Badge */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${
              isTopRank ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'
            }`}
          >
            #{rank}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-bold text-slate-900 text-base">{worker_name}</h4>
              <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-medium">
                {verification_status}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {profession || 'Service Worker'} • {location || 'Service Area'}
            </p>
          </div>
        </div>

        {/* Total Score Display */}
        <div className="text-right shrink-0">
          <div className="text-2xl font-black text-emerald-600 leading-none">
            {score.toFixed(1)}
          </div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Match Score
          </span>
        </div>
      </div>

      {/* Quick Stats Pill Row */}
      <div className="flex flex-wrap gap-3 text-xs bg-slate-50 rounded-lg p-2.5 mb-4 text-slate-600">
        <div className="flex items-center gap-1 font-medium">
          <span className="text-amber-500">⭐</span>
          <span>{rating ? rating.toFixed(1) : 'New'} rating</span>
        </div>
        <div className="flex items-center gap-1 font-medium">
          <span className="text-blue-500">💼</span>
          <span>{experience_years || 0} yrs exp</span>
        </div>
        <div className="flex items-center gap-1 font-medium">
          <span className="text-teal-500">📊</span>
          <span>{total_jobs || 0} completed jobs</span>
        </div>
      </div>

      {/* Score Component Breakdown Progress Bars */}
      <div className="mb-4 bg-white p-3 rounded-lg border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Suitability Factor Analysis
          </h5>
          <span className="text-[10px] text-blue-800 bg-blue-50 px-2 py-0.5 rounded font-semibold border border-blue-200">
            Cooperative Criteria
          </span>
        </div>
        <ScoreBreakdown breakdown={breakdown} />
      </div>

      {/* Dynamic Reason Bullets */}
      <div className="mb-4">
        <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center justify-between">
          <span>Why this worker is recommended:</span>
          <span className="text-[10px] font-normal text-slate-500 italic">Recommended based on service skills, location, availability, experience and bio-economic fatigue metrics</span>
        </h5>
        <ul className="space-y-1 text-xs text-slate-600">
          {reasons && reasons.length > 0 ? (
            reasons.map((reason, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-emerald-600 font-bold shrink-0">✓</span>
                <span>{reason}</span>
              </li>
            ))
          ) : (
            <li className="text-slate-400 italic">No specific reasons generated</li>
          )}
        </ul>
      </div>

      {/* Action Button: Allocate Worker */}
      <div className="pt-3 border-t border-slate-100 flex justify-end">
        <button
          onClick={() => onAllocate && onAllocate(recommendation)}
          disabled={allocating}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center gap-2 disabled:opacity-50"
        >
          <span>👤</span>
          <span>{allocating ? 'Allocating...' : `Assign ${worker_name}`}</span>
        </button>
      </div>
    </div>
  )
}
