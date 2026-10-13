import { useZoneWeather } from '../hooks/useZoneWeather'
import { formatNumber } from '../lib/format'

/**
 * Compact live-weather indicator for a list row: temperature + next-24h rain.
 * Fetches lazily when mounted, so it only requests weather for rows the user
 * actually sees (e.g. after clicking a risk-level card).
 */
export default function ZoneWeatherChip({
  latitude,
  longitude,
}: {
  latitude: number
  longitude: number
}) {
  const { weather, loading } = useZoneWeather(latitude, longitude)

  if (loading && !weather) {
    return <span className="text-[10px] text-slate-400">weather…</span>
  }

  if (!weather) return null

  if (!weather.available) {
    return (
      <span
        className="text-[10px] text-amber-700 font-medium"
        title={weather.reason ?? 'Weather unavailable'}
      >
        ⚠ offline
      </span>
    )
  }

  const temp = weather.current?.temperature_c
  const next24 = weather.summary?.next_24h_precipitation_mm

  return (
    <span className="inline-flex items-center gap-2 text-[10px] text-slate-600 whitespace-nowrap">
      <span title="Current temperature (Open-Meteo)">
        {temp !== null && temp !== undefined ? `${formatNumber(temp, 0)}°C` : '—'}
      </span>
      <span
        className={`font-medium ${
          (next24 ?? 0) >= 40
            ? 'text-blue-700'
            : (next24 ?? 0) >= 10
              ? 'text-sky-600'
              : 'text-slate-400'
        }`}
        title="Forecast precipitation in the next 24 hours (Open-Meteo)"
      >
        🌧 {formatNumber(next24 ?? 0)} mm/24h
      </span>
    </span>
  )
}