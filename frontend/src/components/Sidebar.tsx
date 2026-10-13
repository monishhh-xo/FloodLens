const NAV = [
  { id: 'overview', label: 'Overview' },
  { id: 'assess', label: 'Run assessment' },
  { id: 'hotspots', label: 'Risk hotspots' },
  { id: 'reports', label: 'Community reports' },
  { id: 'model', label: 'Model information' },
]

export default function Sidebar({
  active,
  onNavigate,
  backendOnline,
  weatherOnline,
}: {
  active: string
  onNavigate: (id: string) => void
  backendOnline: boolean
  weatherOnline: boolean
}) {
  return (
    <aside className="w-14 md:w-60 shrink-0 bg-[#0b1220] text-slate-300 flex flex-col sidebar-scroll sticky top-0 h-screen overflow-y-auto">
      <div className="flex items-center gap-3 px-3 md:px-5 py-4 border-b border-white/10">
        <span className="h-9 w-9 shrink-0 rounded-lg bg-gradient-to-br from-sky-500 to-blue-700 flex items-center justify-center text-white text-lg">
          🌊
        </span>
        <div className="hidden md:block">
          <p className="font-bold text-slate-100 text-sm leading-tight">FloodLens AI</p>
          <p className="text-[11px] text-sky-400 mt-0.5">Urban Flood Hotspot Predictor</p>
        </div>
      </div>

      <nav className="flex-1 py-4">
        <p className="hidden md:block px-5 pb-2 text-[10px] uppercase tracking-widest text-slate-500">Dashboard</p>
        <div className="flex md:flex-col gap-1 px-2 md:px-3">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`flex-1 md:flex-none text-center md:text-left px-2 md:px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                active === item.id
                  ? 'bg-sky-600/25 text-sky-300 border border-sky-500/30'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200 border border-transparent'
              }`}
            >
              <span className="hidden md:inline">{item.label}</span>
              <span className="md:hidden" aria-label={item.label}>
                {item.id[0].toUpperCase()}
              </span>
            </button>
          ))}
        </div>
      </nav>

      <div className="px-3 md:px-5 py-4 border-t border-white/10 space-y-2">
        <p className="hidden md:block text-[10px] uppercase tracking-widest text-slate-500 mb-1">Service status</p>
        <div className="flex items-center gap-2 text-[11px]">
          <span className={`h-2 w-2 rounded-full ${backendOnline ? 'bg-emerald-400' : 'bg-red-500'}`} />
          <span className="hidden md:inline">{backendOnline ? 'Backend online' : 'Backend offline'}</span>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <span className={`h-2 w-2 rounded-full ${weatherOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="hidden md:inline">{weatherOnline ? 'Live weather' : 'Weather offline / demo'}</span>
        </div>
        <p className="hidden md:block text-[10px] text-slate-500 mt-2 leading-relaxed">
          Hackathon MVP · Demo Risk Estimates · Not an official warning system
        </p>
      </div>
    </aside>
  )
}