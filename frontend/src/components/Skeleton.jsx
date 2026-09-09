import { motion } from 'framer-motion'

// Skeleton shimmer base
function Skeleton({ className = '', rounded = 'rounded' }) {
  return (
    <div
      className={`relative overflow-hidden bg-slate-200 ${rounded} ${className}`}
    >
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.5) 50%, transparent 100%)',
        }}
        animate={{ x: ['-100%', '100%'] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  )
}

// Card-shaped skeleton for service catalog
export function ServiceCardSkeleton() {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-20" rounded="rounded-full" />
        <Skeleton className="h-6 w-6" rounded="rounded" />
      </div>
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
      <Skeleton className="h-9 w-full" rounded="rounded-lg" />
    </div>
  )
}

// Request card skeleton
export function RequestCardSkeleton() {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-3 w-1/3" />
        </div>
        <Skeleton className="h-6 w-20" rounded="rounded-full" />
      </div>
      <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-2">
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-full" />
      </div>
      <Skeleton className="h-3 w-1/3" />
    </div>
  )
}

// Stat card skeleton
export function StatCardSkeleton() {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10" rounded="rounded-xl" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-6 w-12" />
        </div>
      </div>
    </div>
  )
}

// Dashboard header skeleton
export function DashboardHeaderSkeleton() {
  return (
    <div className="bg-gradient-to-r from-slate-200 to-slate-100 p-8 rounded-2xl space-y-4">
      <Skeleton className="h-5 w-32" rounded="rounded-full" />
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-48" />
    </div>
  )
}

// Full page loading skeleton
export function PageSkeleton({ cards = 6 }) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <DashboardHeaderSkeleton />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: cards }).map((_, i) => (
          <ServiceCardSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}

// Table row skeleton
export function TableRowSkeleton({ cols = 5 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export default Skeleton
