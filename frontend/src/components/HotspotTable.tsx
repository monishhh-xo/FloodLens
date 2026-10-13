import type { AssessResponse, Zone } from '../api/types'
import { formatNumber } from '../lib/format'
import { RiskBadge, ScoreBar } from './ui'

export default function HotspotTable({
  zones,
  lastAssessment,
  onSelectZone,
}: {
  zones: Zone[]
  lastAssessment: AssessResponse | null
  onSelectZone: (id: string) => void
}) {
  const rows = zones
    .filter((zone) => zone.baseline_demo_risk)
    .map((zone) => ({ zone, preview: zone.baseline_demo_risk! }))
    .sort((a, b) => b.preview.score - a.preview.score)

  const assessedZoneId = lastAssessment?.zone.id

  return (
    <div className="overflow-x-auto -mx-5 px-5">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="text-slate-500 border-b border-slate-200">
            <th className="py-2 pr-3 font-medium">Location</th>
            <th className="py-2 pr-3 font-medium">Baseline Demo Risk</th>
            <th className="py-2 pr-3 font-medium">Assumed rainfall</th>
            <th className="py-2 pr-3 font-medium hidden md:table-cell">Top contributing factor</th>
            <th className="py-2 font-medium hidden lg:table-cell">Why</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ zone, preview }) => {
            const top = [...preview.top_factors].sort((a, b) => b.points - a.points)[0]
            const isAssessed = zone.id === assessedZoneId
            return (
              <tr
                key={zone.id}
                className={`border-b border-slate-100 hover:bg-slate-50 ${
                  isAssessed ? 'bg-sky-50' : ''
                }`}
              >
                <td className="py-2.5 pr-3">
                  <button
                    type="button"
                    onClick={() => onSelectZone(zone.id)}
                    className="font-semibold text-slate-800 hover:text-sky-700"
                  >
                    {zone.name}
                  </button>
                  {isAssessed && (
                    <span className="ml-2 text-[10px] font-bold uppercase tracking-wide text-sky-700">
                      just assessed
                    </span>
                  )}
                  <p className="text-slate-400 mt-0.5">
                    {zone.latitude.toFixed(4)}, {zone.longitude.toFixed(4)}
                  </p>
                </td>
                <td className="py-2.5 pr-3">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 w-9">
                      {formatNumber(preview.score)}
                    </span>
                    <RiskBadge level={preview.risk_level} />
                  </div>
                  <div className="mt-1 w-24">
                    <ScoreBar score={preview.score} color={preview.color} />
                  </div>
                </td>
                <td className="py-2.5 pr-3 text-slate-600">
                  <p>{formatNumber(preview.assumed_rainfall_mm_1h)} mm/1 h</p>
                  <p>{formatNumber(preview.assumed_rainfall_mm_24h)} mm/24 h</p>
                  <p className="text-[10px] text-slate-400">illustrative baseline</p>
                </td>
                <td className="py-2.5 pr-3 hidden md:table-cell">
                  {top ? (
                    <div>
                      <p className="font-medium text-slate-700">{top.label}</p>
                      <p className="text-slate-400">{formatNumber(top.points)} pts</p>
                    </div>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
                <td className="py-2.5 hidden lg:table-cell text-slate-500 max-w-[220px]">
                  <span className="line-clamp-2">{preview.note}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-3 text-[11px] text-slate-400 leading-snug">
        Scores are Demo Risk Estimates computed by the transparent rule engine using a documented
        assumed rainfall input and illustrative zone attributes. They are not predictions from the
        synthetic-data prototype model.
      </p>
    </div>
  )
}