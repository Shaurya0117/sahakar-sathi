import React, { useEffect, useState } from 'react'
import { allocateWorker } from '../../services/bookingService'
import { getMatchingRecommendations } from '../../services/matchingService'
import RecommendationCard from './RecommendationCard'

export default function MatchingModal({ request, onClose, onSuccess }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  // Allocation State
  const [allocatingWorkerId, setAllocatingWorkerId] = useState(null)
  const [confirmWorker, setConfirmWorker] = useState(null)
  const [allocError, setAllocError] = useState(null)

  useEffect(() => {
    if (!request?.id) return

    let isMounted = true
    setLoading(true)
    setError(null)

    getMatchingRecommendations(request.id)
      .then((res) => {
        if (isMounted) {
          setData(res.data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || 'Failed to fetch worker recommendations')
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [request])

  const handleConfirmAllocate = async () => {
    if (!confirmWorker || !request) return

    setAllocatingWorkerId(confirmWorker.worker_id)
    setAllocError(null)

    try {
      await allocateWorker(request.id, confirmWorker.worker_id)
      setConfirmWorker(null)
      onSuccess && onSuccess(`Successfully allocated ${confirmWorker.worker_name} to Request #${request.id}`)
      onClose && onClose()
    } catch (err) {
      setAllocError(err.response?.data?.detail || 'Failed to allocate worker.')
      setAllocatingWorkerId(null)
    }
  }

  if (!request) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden border border-slate-100 relative">
        {/* Modal Header */}
        <div className="p-6 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="bg-blue-500/20 text-blue-300 font-bold text-xs px-2 py-0.5 rounded border border-blue-500/30">
                WORKER RECOMMENDATIONS
              </span>
              <span className="text-xs text-slate-400">Request #{request.id}</span>
            </div>
            <h3 className="text-xl font-bold">Recommended Workers for Allocation</h3>
            <p className="text-xs text-slate-300 mt-0.5">
              Service: <span className="text-white font-medium">{data?.service_name || request.service_name || 'Service'}</span> • Location: <span className="text-white font-medium">{request.location}</span>
            </p>
            {request.image_url && (
              <div className="mt-3">
                <p className="text-xs font-bold text-slate-400 uppercase mb-1">Attached Photo</p>
                <img src={`http://localhost:8000${request.image_url}`} alt="Request Photo" className="max-h-24 rounded border border-slate-700 object-cover" />
              </div>
            )}
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        {/* Cooperative Allocation Criteria Banner */}
        <div className="bg-slate-100 border-b border-slate-200 px-6 py-3 text-xs text-slate-800 flex items-center gap-2">
          <span className="text-base">🤝</span>
          <span>
            <strong>Cooperative Allocation Policy:</strong> Workers are recommended based on service skills, location, availability, experience and current workload to promote equitable work opportunity.
          </span>
        </div>

        {/* Allocation Error Alert */}
        {allocError && (
          <div className="bg-rose-50 border-b border-rose-200 px-6 py-3 text-xs text-rose-700 font-medium flex items-center justify-between">
            <span>⚠️ {allocError}</span>
            <button onClick={() => setAllocError(null)} className="text-rose-500 hover:text-rose-700">✕</button>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {loading ? (
            <div className="py-12 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-emerald-500 border-t-transparent mb-3"></div>
              <p className="text-sm font-medium text-slate-600">Running candidate discovery & multi-factor scoring...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 text-rose-700 text-sm rounded-xl border border-rose-200">
              ⚠️ {error}
            </div>
          ) : data?.candidate_count === 0 ? (
            <div className="py-12 text-center text-slate-500 bg-slate-50 rounded-xl border border-slate-200 p-8">
              <p className="text-3xl mb-2">🔍</p>
              <h4 className="font-bold text-slate-800 text-base">No Eligible Workers Found</h4>
              <p className="text-xs mt-1 max-w-md mx-auto text-slate-500">
                No verified, available cooperative workers matched the required skill or location criteria for this request.
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
                <span>Found <strong>{data.candidate_count}</strong> eligible candidate(s)</span>
                <span className="italic">Ranked by total suitability score</span>
              </div>

              <div className="space-y-4">
                {data.recommendations.map((rec, index) => (
                  <RecommendationCard
                    key={rec.worker_id}
                    rank={index + 1}
                    recommendation={rec}
                    onAllocate={(workerRec) => setConfirmWorker(workerRec)}
                    allocating={allocatingWorkerId === rec.worker_id}
                  />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold text-sm rounded-xl transition"
          >
            Close
          </button>
        </div>

        {/* Confirmation Modal */}
        {confirmWorker && (
          <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-6 z-20">
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-100 text-slate-800">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-2xl mb-4 mx-auto">
                🤝
              </div>
              <h4 className="text-lg font-bold text-center mb-1">Confirm Worker Allocation</h4>
              <p className="text-xs text-slate-500 text-center mb-4">
                Assign <strong className="text-slate-800">{confirmWorker.worker_name}</strong> to Request #{request.id} ({data?.service_name})?
              </p>
              <div className="bg-slate-50 p-3 rounded-xl mb-5 text-xs text-slate-600 space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Match Score:</span>
                  <strong className="text-emerald-600">{confirmWorker.score.toFixed(1)}/100</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Location:</span>
                  <span>{confirmWorker.location}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setConfirmWorker(null)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmAllocate}
                  disabled={allocatingWorkerId !== null}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-md transition disabled:opacity-50"
                >
                  {allocatingWorkerId !== null ? 'Allocating...' : 'Confirm Assignment'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
