/**
 * ServiceCatalogCard — preview of registered services in the cooperative catalog.
 */
export default function ServiceCatalogCard({ services }) {
  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100">Service Catalog Foundation</h2>
          <p className="text-xs text-slate-400">Services supported by the cooperative</p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-lg bg-primary-500/10 text-primary-400 font-semibold border border-primary-500/20">
          {services.length} Services Active
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {services.map((svc) => (
          <div key={svc.id} className="bg-white/3 p-3.5 rounded-xl border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-primary-400 uppercase tracking-wider">{svc.category}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="font-semibold text-slate-100 text-sm">{svc.name}</p>
            <p className="text-xs text-slate-400 mt-1 line-clamp-2">{svc.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
