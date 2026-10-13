import type { Zone } from '../api/types'
import { RISK_HEX, formatNumber } from '../lib/format'
import { Badge, RiskBadge, ScoreBar } from './ui'
import ZoneWeatherChip from './ZoneWeatherChip'

export type RiskLevelFilter = 'Low' | 'Moderate' | 'High' | 'Severe' | null

const LEVELS = ['Low', 'Moderate', 'High', 'Severe'] as const

const LEVEL_GUIDE: Record<string, string> = {
  Low:
    'Low band — modelled risk below 25/100 under the assumed rainfall. Low-lying terrain with better drainage.',
  Moderate:
    'Moderate band — 25 to 49/100. Some rainfall contribution plus illustrative terrain/drainage assumptions.',
  High:
    'High band — 50 to 74/100. Higher assumed rainfall or weaker drainage pushes the modelled score up.',
  Severe:
    'Severe band — 75 to 100/100. Heavy assumed rainfall across a low-lying, impervious, poorly drained zone.',
}

function ZoneRow({
  zone,
  onSelect,
}: {
  zone: Zone
  onSelect: (id: string) => void
}) {
  const preview = zone.baseline_demo_risk
  if (!preview) return null

  const top = [...preview.top_factors].sort((a, b) => b.points - a.points)[0]

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(zone.id)}
        className="w-full text-left rounded-md border border-slate-200 hover:border-sky-400 hover:bg-sky-50/60 transition-colors px-3 py-2"
      >
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-semibold text-slate-800 text-sm truncate">{zone.name}</span>
            <RiskBadge level={preview.risk_level} />
          </div>
          <span className="text-sm font-bold text-slate-900 tabular-nums">
            {formatNumber(preview.score)}
            <span className="text-[10px] font-normal text-slate-400">/100</span>
          </span>
        </div>
        <div className="mt-1.5 w-full max-w-[220px]">
          <ScoreBar score={preview.score} color={preview.color} />
        </div>
        <div className="mt-1.5 flex items-center gap-x-3 gap-y-1 flex-wrap text-[11px] text-slate-500">
          <span className="tabular-nums">
            {zone.latitude.toFixed(4)}, {zone.longitude.toFixed(4)}
          </span>
          <span>
            drainage {formatNumber(zone.drainage_capacity_index, 2)} · elev {zone.elevation_class}{' '}
            · imperv {formatNumber(zone.imperviousness_pct, 0)}%
          </span>
        </div>
        {top && (
          <p className="mt-1 text-[11px] text-slate-600">
            Top factor: <strong>{top.label}</strong> ({formatNumber(top.points)} pts)
          </p>
        )}
        <div className="mt-1">
          <ZoneWeatherChip latitude={zone.latitude} longitude={zone.longitude} />
        </div>
      </button>
    </li>
  )
}

export default function RiskSummaryCards({
  zones,
  activeFilter,
  onFilterChange,
  onSelectZone,
}: {
  zones: Zone[]
  activeFilter: RiskLevelFilter
  onFilterChange: (level: RiskLevelFilter) => void
  onSelectZone: (id: string) => void
}) {
  const counts: Record<string, number> = { Low: 0, Moderate: 0, High: 0, Severe: 0 }
  let total = 0
  let sum = 0
  for (const zone of zones) {
    const preview = zone.baseline_demo_risk
    if (!preview) continue
    counts[preview.risk_level] = (counts[preview.risk_level] ?? 0) + 1
    total += 1
    sum += preview.score
  }

  const bandZones = activeFilter
    ? zones.filter((z) => z.baseline_demo_risk?.risk_level === activeFilter)
    : []

  return (
    <div className="space-y-3">
      <div>
        <p className="text-[11px] text-slate-500 mb-1.5">
          Tap a risk level to see the areas in that band with details & live weather →
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {LEVELS.map((level) => {
            const active = activeFilter === level
            return (
              <button
                key={level}
                type="button"
                onClick={() => onFilterChange(active ? null : level)}
                aria-pressed={active}
                title={LEVEL_GUIDE[level]}
                className={`rounded-lg border px-4 py-3 flex items-center gap-3 text-left transition-all shadow-sm ${
                  active
                    ? 'border-slate-900 ring-2 ring-offset-1 bg-slate-50'
                    : 'border-slate-200 bg-white hover:border-slate-400'
                }`}
                style={active ? { borderColor: RISK_HEX[level] } : undefined}
              >
                <span
                  className="h-9 w-9 shrink-0 rounded-full flex items-center justify-center text-white text-sm font-bold"
                  style={{ backgroundColor: RISK_HEX[level] }}
                >
                  {counts[level] ?? 0}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-slate-800">{level}</span>
                  <span className="block text-[11px] text-slate-500">
                    {active ? 'showing areas' : 'baseline zones'}
                  </span>
                </span>
              </button>
            )
          })}

          <div className="rounded-lg border border-slate-200 bg-[#0b1220] text-white shadow-sm px-4 py-3 flex items-center gap-3">
            <span className="h-9 w-9 shrink-0 rounded-full bg-white/10 flex items-center justify-center text-white text-sm font-bold">
              {total > 0 ? Math.round(sum / total) : '—'}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold">Mean baseline</p>
              <p className="text-[11px] text-slate-400 truncate">score /100 across zones</p>
            </div>
          </div>
        </div>
      </div>

      {activeFilter && (
        <div
          className="rounded-lg border bg-white shadow-sm overflow-hidden"
          style={{ borderColor: `${RISK_HEX[activeFilter]}80` }}
        >
          <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-100">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="h-2.5 w-2.5 rounded-full shrink-0"
                style={{ backgroundColor: RISK_HEX[activeFilter] }}
              />
              <p className="text-sm font-semibold text-slate-800 truncate">
                {activeFilter} band — {bandZones.length} area{bandZones.length === 1 ? '' : 's'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onFilterChange(null)}
              className="text-xs font-medium text-slate-500 hover:text-slate-800"
            >
              ✕ clear filter
            </button>
          </div>

          <p className="px-4 pt-2 text-[11px] text-slate-500 leading-snug">
            {LEVEL_GUIDE[activeFilter]}
          </p>

          {bandZones.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-500">
              No zones fall in the {activeFilter} band under the baseline assumed rainfall.
            </p>
          ) : (
            <ul className="p-3 space-y-2 max-h-[340px] overflow-y-auto">
              {bandZones.map((zone) => (
                <ZoneRow key={zone.id} zone={zone} onSelect={onSelectZone} />
              ))}
            </ul>
          )}

          <div className="px-4 py-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
            <Badge tone="blue">live weather via Open-Meteo</Badge>
            <Badge tone="amber">scores are illustrative Demo Risk Estimates</Badge>
            <span className="text-[10px] text-slate-400">
              Click an area to highlight it on the map and open its detail panel.
            </span>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <Badge tone="blue">Baseline rainfall assumed: 12 mm/1 h · 75 mm/24 h</Badge>
        <Badge tone="amber">Illustrative Demo Risk Estimates</Badge>
        <span>Run an assessment for a live rainfall-driven score.</span>
      </div>
    </div>
  )
}