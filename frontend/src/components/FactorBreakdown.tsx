import type { RiskFactor } from '../api/types'
import { formatNumber } from '../lib/format'

export default function FactorBreakdown({ factors }: { factors: RiskFactor[] }) {
  const weather = factors.filter((f) => f.bucket === 'weather')
  const illustrative = factors.filter((f) => f.bucket === 'illustrative')

  function group(label: string, items: RiskFactor[]) {
    if (items.length === 0) return null
    return (
      <div className="mb-3">
        <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1.5">{label}</p>
        <div className="space-y-2.5">
          {items.map((factor) => (
            <div key={factor.key}>
              <div className="flex items-baseline justify-between gap-2 text-xs">
                <span className="text-slate-700 font-medium">{factor.label}</span>
                <span className="text-slate-500 whitespace-nowrap">
                  {formatNumber(factor.points)} pts
                  {factor.input_value !== null && factor.input_value !== undefined
                    ? ` · ${formatNumber(Number(factor.input_value))} ${factor.input_unit}`
                    : ''}
                </span>
              </div>
              <div className="factor-bar-track mt-1">
                <div
                  className="h-full rounded"
                  style={{
                    width: `${Math.max(0, Math.min(100, (factor.points / factor.weight_max) * 100))}%`,
                    backgroundColor: factor.bucket === 'weather' ? '#0284c7' : '#7c3aed',
                  }}
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">{factor.note}</p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      {group('Weather-derived inputs', weather)}
      {group('Illustrative terrain & drainage assumptions', illustrative)}
      <p className="text-[11px] text-slate-400 leading-snug">
        Blue bars = weather-derived evidence · Purple bars = illustrative assumptions that can be
        replaced with surveyed data later.
      </p>
    </div>
  )
}