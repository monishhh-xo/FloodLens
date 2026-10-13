import type { WeatherResponse } from '../api/types'
import { formatNumber, formatRelative } from '../lib/format'
import { Badge, Spinner } from './ui'

/** Small bar chart of the next 12 hourly precipitation values. */
function HourlyStrip({ hourly }: { hourly: WeatherResponse['hourly'] }) {
  const slice = hourly.slice(0, 12)
  if (slice.length === 0) return null

  const peak = Math.max(
    1,
    ...slice.map((h) => h.precipitation_mm ?? 0),
  )

  return (
    <div>
      <div className="flex items-end gap-[3px] h-10">
        {slice.map((hour, index) => {
          const mm = hour.precipitation_mm ?? 0
          const height = Math.max(6, Math.round((mm / peak) * 100))
          const color = mm >= 5 ? '#1d4ed8' : mm >= 1.5 ? '#0284c7' : '#7dd3fc'
          const time = hour.time.slice(11, 16)
          return (
            <div
              key={index}
              className="flex-1 rounded-t"
              title={`${time} · ${formatNumber(mm)} mm`}
              style={{
                height: `${height}%`,
                backgroundColor: color,
                minWidth: 6,
              }}
            />
          )
        })}
      </div>
      <div className="flex justify-between text-[9px] text-slate-400 mt-1">
        <span>{slice[0]?.time.slice(11, 16)}</span>
        <span className="uppercase">next {slice.length} h</span>
        <span>{slice[slice.length - 1]?.time.slice(11, 16)}</span>
      </div>
    </div>
  )
}

/** Live Open-Meteo weather card with source, units, timestamp and refresh. */
export default function WeatherCard({
  weather,
  loading,
  error,
  onRefresh,
  compact,
}: {
  weather: WeatherResponse | null
  loading: boolean
  error: string | null
  onRefresh?: () => void
  compact?: boolean
}) {
  if (error && !weather) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
        Weather request failed: {error}
      </div>
    )
  }

  if (!weather) {
    return loading ? <Spinner label="Fetching live weather…" /> : null
  }

  if (!weather.available) {
    return (
      <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge tone="amber">OFFLINE / DEMO STATE</Badge>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="text-[11px] font-medium text-amber-800 underline"
            >
              retry
            </button>
          )}
        </div>
        <p className="text-[11px] text-amber-800 mt-1.5 leading-snug">
          {weather.reason ?? 'The upstream weather service could not be reached.'} No values are
          estimated or substituted.
        </p>
      </div>
    )
  }

  const current = weather.current
  const summary = weather.summary

  return (
    <div className="rounded-md border border-sky-200 bg-gradient-to-b from-sky-50 to-white px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold text-sky-900 uppercase tracking-wide">
          ☁ Live weather · Open-Meteo
        </p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="text-[11px] font-medium text-sky-700 hover:text-sky-900"
            title="Refresh live weather"
          >
            ↻ refresh
          </button>
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        {current?.temperature_c !== null && current?.temperature_c !== undefined && (
          <span className="text-2xl font-black text-slate-900">
            {formatNumber(current.temperature_c, 1)}
            <span className="text-sm font-semibold text-slate-500"> °C</span>
          </span>
        )}
        {current?.relative_humidity_pct !== null && current?.relative_humidity_pct !== undefined && (
          <span className="text-xs text-slate-600">
            💧 {formatNumber(current.relative_humidity_pct, 0)}% humidity
          </span>
        )}
        <span className="text-xs text-slate-600">
          🌧 now {formatNumber(current?.precipitation_mm ?? 0)} mm
          {weather.units?.precipitation ? ` (${weather.units.precipitation})` : ''}
        </span>
      </div>

      {summary && (
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-slate-700">
          <span>
            Next 24 h:{' '}
            <strong>{formatNumber(summary.next_24h_precipitation_mm)} mm</strong>
          </span>
          <span>
            Peak hour:{' '}
            <strong>
              {formatNumber(summary.next_24h_peak_hourly_mm)} mm
              {summary.next_24h_peak_hour ? ` @ ${summary.next_24h_peak_hour.slice(11, 16)}` : ''}
            </strong>
          </span>
          <span>
            Max probability:{' '}
            <strong>
              {summary.next_24h_max_probability_pct !== null &&
              summary.next_24h_max_probability_pct !== undefined
                ? `${summary.next_24h_max_probability_pct}%`
                : '—'}
            </strong>
          </span>
          <span>
            Hours covered: <strong>{summary.hours_covered}</strong>
          </span>
        </div>
      )}

      {!compact && weather.hourly.length > 0 && (
        <div className="mt-2.5">
          <HourlyStrip hourly={weather.hourly} />
        </div>
      )}

      <p className="mt-2 text-[9px] text-slate-400 leading-snug">
        {weather.source} · retrieved {formatRelative(weather.retrieved_at_utc)} · forecast for the
        requested coordinates, not a local rain gauge.
      </p>
    </div>
  )
}