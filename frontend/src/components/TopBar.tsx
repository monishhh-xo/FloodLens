import type { HealthResponse } from '../api/types'
import { Badge } from './ui'
import { formatRelative } from '../lib/format'

export default function TopBar({
  health,
  weatherSource,
  weatherRetrievedAt,
  weatherAvailable,
}: {
  health: HealthResponse | null
  weatherSource: string | null
  weatherRetrievedAt: string | null
  weatherAvailable: boolean | null
}) {
  return (
    <header className="bg-white border-b border-slate-200 px-4 md:px-6 py-3 flex flex-wrap items-center gap-3">
      <div className="mr-auto">
        <h1 className="text-base md:text-lg font-bold text-slate-900 leading-tight">
          Chennai Flood Risk Dashboard
        </h1>
        <p className="text-xs text-slate-500">Focus city: Chennai, Tamil Nadu, India</p>
      </div>

      <Badge tone="amber">DEMO</Badge>
      <Badge tone="blue">MVP prototype</Badge>
      {weatherAvailable !== null &&
        (weatherAvailable ? (
          <Badge tone="green">Weather: live forecast</Badge>
        ) : (
          <Badge tone="red">Weather: offline / demo state</Badge>
        ))}

      <div className="flex flex-col items-end text-[11px] text-slate-500">
        <span className="max-w-[240px] truncate">{weatherSource ?? 'Weather source: —'}</span>
        <span>Retrieved {formatRelative(weatherRetrievedAt)}</span>
        {health && <span>API {health.version} · {health.status}</span>}
      </div>
    </header>
  )
}