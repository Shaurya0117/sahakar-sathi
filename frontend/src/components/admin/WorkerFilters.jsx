/**
 * WorkerFilters — Search input + verification filter + availability filter
 */
export default function WorkerFilters({
  searchTerm,
  setSearchTerm,
  verificationFilter,
  setVerificationFilter,
  availabilityFilter,
  setAvailabilityFilter,
}) {
  return (
    <div className="glass-card p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
      {/* Search Input */}
      <div className="relative w-full md:w-80">
        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
          🔍
        </span>
        <input
          id="admin-worker-search"
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by worker name, profession, location..."
          className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-primary-500 transition-colors"
        />
      </div>

      {/* Filter Pill Buttons */}
      <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
        {/* Verification Filter */}
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
          <span className="px-2 text-slate-400 font-semibold">Status:</span>
          {['ALL', 'PENDING', 'VERIFIED', 'REJECTED'].map((status) => (
            <button
              key={status}
              type="button"
              id={`filter-verification-${status.toLowerCase()}`}
              onClick={() => setVerificationFilter(status)}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                verificationFilter === status
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              {status === 'ALL' ? 'All' : status.charAt(0) + status.slice(1).toLowerCase()}
            </button>
          ))}
        </div>

        {/* Availability Filter */}
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 text-xs">
          <span className="px-2 text-slate-400 font-semibold">Availability:</span>
          {['ALL', 'AVAILABLE', 'UNAVAILABLE'].map((avail) => (
            <button
              key={avail}
              type="button"
              id={`filter-availability-${avail.toLowerCase()}`}
              onClick={() => setAvailabilityFilter(avail)}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                availabilityFilter === avail
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              {avail === 'ALL' ? 'All' : avail.charAt(0) + avail.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
