import { Fragment, useEffect, useRef, useState } from 'react'
import type { Popup as LeafletPopup } from 'leaflet'
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip } from 'react-leaflet'
import type { Zone } from '../api/types'
import { RISK_HEX, formatNumber } from '../lib/format'
import { RiskBadge, Spinner } from './ui'
import { useZoneWeather } from '../hooks/useZoneWeather'
import { useZoneForecasts } from '../hooks/useZoneForecasts'
import type { RiskLevelFilter } from './RiskSummaryCards'

const CHENNAI_CENTER: [number, number] = [13.0827, 80.2707]

const LEVELS = ['Low', 'Moderate', 'High', 'Severe'] as const

/** Popup that only fetches live weather once the user actually opens it. */
function ZonePopup({
  zone,
  onSelect,
}: {
  zone: Zone
  onSelect: (zoneId: string) => void
}) {
  const [open, setOpen] = useState(false)
  const popupRef = useRef<LeafletPopup | null>(null)

  useEffect(() => {
    const popup = popupRef.current
    if (!popup) return undefined
    const onOpen = () => setOpen(true)
    const onClose = () => setOpen(false)
    popup.on('open', onOpen)
    popup.on('close', onClose)
    return () => {
      popup.off('open', onOpen)
      popup.off('close', onClose)
    }
  }, [])

  const { weather, loading } = useZoneWeather(
    open ? zone.latitude : null,
    open ? zone.longitude : null,
  )
  const risk = zone.baseline_demo_risk

  return (
    <Popup ref={popupRef}>
      <div className="text-xs min-w-[210px] max-w-[250px]">
        <p className="font-bold text-slate-900 text-sm">{zone.name}</p>
        <p className="text-slate-500 mt-0.5">
          {zone.latitude.toFixed(4)}, {zone.longitude.toFixed(4)}
        </p>
        {risk ? (
          <div className="mt-2 flex items-center justify-between">
            <RiskBadge level={risk.risk_level} />
            <span className="font-semibold text-slate-800">{risk.score.toFixed(1)}/100</span>
          </div>
        ) : (
          <p className="text-slate-500 mt-1">No baseline preview.</p>
        )}

        {/* Live Open-Meteo weather for this exact point */}
        <div className="mt-2">
          {loading && !weather ? (
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <Spinner /> loading live weather…
            </div>
          ) : weather?.available ? (
            <div className="rounded border border-sky-200 bg-sky-50 px-2 py-1.5">
              <p className="text-[9px] uppercase tracking-wide text-sky-800 font-semibold">
                ☁ Live · Open-Meteo
              </p>
              <p className="text-[11px] text-slate-700 mt-0.5">
                {formatNumber(weather.current?.temperature_c ?? null, 0)}°C · 💧{' '}
                {formatNumber(weather.current?.relative_humidity_pct ?? null, 0)}%
              </p>
              <p className="text-[11px] text-slate-700">
                🌧 now {formatNumber(weather.current?.precipitation_mm ?? 0)} mm · next 24 h{' '}
                <strong>
                  {formatNumber(weather.summary?.next_24h_precipitation_mm ?? 0)} mm
                </strong>
              </p>
              <p className="text-[9px] text-slate-400 mt-0.5">forecast for this location</p>
            </div>
          ) : (
            <div className="rounded border border-amber-200 bg-amber-50 px-2 py-1.5">
              <p className="text-[10px] text-amber-800 font-medium">⚠ Weather offline/demo state</p>
              <p className="text-[9px] text-amber-700 mt-0.5">
                {weather?.reason ?? 'No values are substituted.'}
              </p>
            </div>
          )}
        </div>

        <p className="text-[10px] text-slate-400 mt-1.5 italic">
          Demo zone — not a verified flood hotspot.
        </p>
        <button
          type="button"
          onClick={() => onSelect(zone.id)}
          className="mt-2 w-full px-2 py-1 rounded bg-sky-700 text-white text-[11px] font-semibold hover:bg-sky-800"
        >
          Inspect {zone.name}
        </button>
      </div>
    </Popup>
  )
}

export default function ZoneMap({
  zones,
  selectedId,
  riskFilter,
  onSelect,
}: {
  zones: Zone[]
  selectedId: string | null
  riskFilter: RiskLevelFilter
  onSelect: (zoneId: string) => void
}) {
  const forecasts = useZoneForecasts(zones)
  const centre = useZoneWeather(CHENNAI_CENTER[0], CHENNAI_CENTER[1])
  const centreRain = centre.weather?.available
    ? (centre.weather.summary?.next_24h_precipitation_mm ?? null)
    : null

  /** Halo radius (px) scaled with the forecast amount — bigger drop, bigger ring. */
  const rainRadius = (mm: number) => 10 + 3 * Math.sqrt(Math.min(mm, 60))

  return (
    <div className="relative h-[420px] rounded-lg overflow-hidden border border-slate-200 shadow-sm">
      <MapContainer center={CHENNAI_CENTER} zoom={12} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {zones.map((zone) => {
          const risk = zone.baseline_demo_risk
          const color = risk ? RISK_HEX[risk.risk_level] : '#64748b'
          const selected = zone.id === selectedId
          const inFilter = !riskFilter || risk?.risk_level === riskFilter
          const forecast = forecasts.data[zone.id]
          const rainMm = forecast?.available
            ? (forecast.summary?.next_24h_precipitation_mm ?? null)
            : null
          return (
            <Fragment key={zone.id}>
              {/* Open-Meteo rain forecast halo (next 24 h) drawn under the marker */}
              {rainMm !== null && rainMm > 0 && (
                <CircleMarker
                  center={[zone.latitude, zone.longitude]}
                  radius={rainRadius(rainMm)}
                  pathOptions={{
                    color: '#0284c7',
                    weight: 1,
                    dashArray: '4 4',
                    fillColor: '#0ea5e9',
                    fillOpacity: inFilter ? 0.22 : 0.06,
                    interactive: false,
                  }}
                />
              )}
              <CircleMarker
                center={[zone.latitude, zone.longitude]}
                radius={selected ? 12 : inFilter && riskFilter ? 11 : 9}
                pathOptions={{
                  color: inFilter ? '#0f172a' : '#94a3b8',
                  weight: selected ? 2.5 : 1,
                  fillColor: color,
                  fillOpacity: inFilter ? (selected ? 0.95 : 0.8) : 0.18,
                }}
                eventHandlers={{ click: () => onSelect(zone.id) }}
              >
                <Tooltip direction="top" offset={[0, -10]}>
                  <div className="text-[11px] leading-snug">
                    <strong>{zone.name}</strong>
                    {risk ? (
                      <>
                        {' · '}
                        <span style={{ color: color, fontWeight: 700 }}>{risk.risk_level}</span>{' '}
                        ({risk.score.toFixed(1)}/100)
                      </>
                    ) : null}
                    <br />
                    🌧 Rain forecast next 24 h:{' '}
                    {rainMm !== null ? (
                      <strong>{formatNumber(rainMm, 1)} mm</strong>
                    ) : forecasts.loading ? (
                      <span>loading…</span>
                    ) : (
                      <span>unavailable</span>
                    )}
                  </div>
                </Tooltip>
                <ZonePopup zone={zone} onSelect={onSelect} />
              </CircleMarker>
            </Fragment>
          )
        })}
      </MapContainer>

      {/* Live Chennai-wide weather chip (top-right) */}
      <div className="absolute top-3 right-3 z-[500] bg-white/95 rounded-md border border-sky-200 px-3 py-2 text-[11px] text-slate-700 shadow max-w-[230px]">
        <p className="text-[9px] uppercase tracking-wide text-sky-800 font-semibold">
          ☁ Open-Meteo live weather · Chennai centre
        </p>
        <p className="mt-0.5 text-slate-700">
          🌧 Rain next 24 h:{' '}
          {centreRain !== null ? (
            <strong>{formatNumber(centreRain, 1)} mm</strong>
          ) : centre.loading ? (
            <span className="text-slate-400">loading forecast…</span>
          ) : (
            <span className="text-amber-700">unavailable</span>
          )}
        </p>
        <p className="mt-0.5 text-slate-500 text-[10px]">
          Hover a zone for its risk category + rain forecast; click for full details.
        </p>
      </div>

      {/* Legend overlay */}
      <div className="absolute bottom-3 left-3 z-[500] bg-white/95 rounded-md border border-slate-200 px-3 py-2 text-[11px] text-slate-700 shadow">
        <div className="flex items-center gap-3">
          {LEVELS.map((level) => (
            <span
              key={level}
              className={`flex items-center gap-1 ${
                riskFilter && riskFilter !== level ? 'opacity-40' : ''
              }`}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: RISK_HEX[level] }} />
              {level}
            </span>
          ))}
        </div>
        <div className="mt-1.5 flex items-center gap-2">
          <span
            className="inline-block h-3.5 w-3.5 rounded-full border border-dashed border-sky-700 bg-sky-500/30"
            aria-hidden
          />
          <span>Rain forecast next 24 h (circle size ∝ mm, Open-Meteo)</span>
        </div>
        <p className="mt-1 text-[10px] text-slate-400">
          {riskFilter
            ? `Filtered: only ${riskFilter} zones shown in colour.`
            : 'Illustrative zones with baseline Demo Risk Estimate (assumed rainfall).'}
        </p>
      </div>
    </div>
  )
}
