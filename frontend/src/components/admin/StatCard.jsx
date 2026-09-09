/**
 * StatCard — displays single statistic metric with icon and background glow.
 */
export default function StatCard({ label, value, icon, color = 'primary', subtitle }) {
  const colorStyles = {
    primary: 'from-primary-500/20 to-primary-600/10 border-primary-500/30 text-primary-400',
    emerald: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400',
    amber: 'from-amber-500/20 to-amber-600/10 border-amber-500/30 text-amber-400',
    rose: 'from-rose-500/20 to-rose-600/10 border-rose-500/30 text-rose-400',
    sky: 'from-sky-500/20 to-sky-600/10 border-sky-500/30 text-sky-400',
  }

  const selectedColor = colorStyles[color] || colorStyles.primary

  return (
    <div className={`glass-card p-5 bg-gradient-to-br ${selectedColor} border transition-all duration-300 hover:scale-[1.02]`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
          <p className="text-3xl font-black text-slate-100 mt-1">{value ?? 0}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className="text-3xl opacity-80">{icon}</div>
      </div>
    </div>
  )
}
