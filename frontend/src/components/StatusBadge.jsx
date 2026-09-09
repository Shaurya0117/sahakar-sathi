/**
 * StatusBadge — displays backend connectivity status.
 */
export default function StatusBadge({ status, loading, error }) {
  if (loading) {
    return (
      <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
        Connecting…
      </span>
    )
  }

  if (error || status !== 'ok') {
    return (
      <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
        <span className="w-2 h-2 rounded-full bg-red-400" />
        Backend offline
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-primary-500/10 text-primary-400 border border-primary-500/20 animate-pulse-glow">
      <span className="w-2 h-2 rounded-full bg-primary-400" />
      Backend live
    </span>
  )
}
