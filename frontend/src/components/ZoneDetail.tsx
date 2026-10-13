import type { Zone } from '../api/types'
import { formatNumber } from '../lib/format'
import { Badge, RiskBadge, ScoreBar } from './ui'
import WeatherCard from './WeatherCard'
import { useZoneWeather } from '../hooks/useZoneWeather'

export default function ZoneDetail({
  zone,
  onUseInAssessment,
}: {
  zone: Zone | null
  onUseInAssessment: (zone: Zone) => void
}) {
  // Live Open-Meteo weather for the selected zone's exact coordinates.
  const zoneWeather = useZoneWeather(
    zone ? zone.latitude : null,
    zone ? zone.longitude : null,
  )

  if (!zone) {
    return (
      <div className="text-sm text-slate-500 py-8 text-center">
        Select a zone on the map or in the dropdown to inspect its details.
      </div>
    )
  }

  const preview = zone.baseline_demo_risk

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-bold text-slate-900">{zone.name}</h3>
        {preview && <RiskBadge level={preview.risk_level} />}
      </div>
      <p className="text-xs text-slate-500 mt-0.5">
        {zone.latitude.toFixed(4)}, {zone.longitude.toFixed(4)} · OSM locality centroid
      </p>
      <p className="text-xs text-slate-600 mt-2 leading-relaxed">{zone.descriptive_note}</p>

      {/* Live Open-Meteo weather for this zone */}
      <div className="mt-3">
        <WeatherCard
          weather={zoneWeather.weather}
          loading={zoneWeather.loading}
          error={zoneWeather.error}
          onRefresh={zoneWeather.refresh}
          compact
        />
      </div>

      {preview && (
        <div className="mt-3">
          <div className="flex items-baseline justify-between text-sm">
            <span className="text-slate-600">Baseline Demo Risk Estimate</span>
            <span className="font-bold text-slate-900">{formatNumber(preview.score)}/100</span>
          </div>
          <ScoreBar score={preview.score} color={preview.color} />
          <p className="text-[11px] text-slate-500 mt-1.5">{preview.note}</p>
        </div>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <div>
          <dt className="text-slate-500">Drainage capacity</dt>
          <dd className="font-medium text-slate-800">{formatNumber(zone.drainage_capacity_index, 2)} / 1</dd>
        </div>
        <div>
          <dt className="text-slate-500">Elevation class</dt>
          <dd className="font-medium text-slate-800">{zone.elevation_class}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Impervious surface</dt>
          <dd className="font-medium text-slate-800">{formatNumber(zone.imperviousness_pct)} %</dd>
        </div>
        <div>
          <dt className="text-slate-500">Water body distance</dt>
          <dd className="font-medium text-slate-800">{formatNumber(zone.water_proximity_m)} m</dd>
        </div>
        <div>
          <dt className="text-slate-500">Land cover / soil</dt>
          <dd className="font-medium text-slate-800">
            {zone.land_cover} / {zone.soil_type}
          </dd>
        </div>
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone="amber">attributes illustrative</Badge>
        <Badge tone="slate">not a verified flood hotspot</Badge>
      </div>

      <button
        type="button"
        onClick={() => onUseInAssessment(zone)}
        className="mt-4 w-full px-3 py-2 rounded-md bg-sky-700 text-white text-sm font-semibold hover:bg-sky-800 transition-colors"
      >
        Use {zone.name} in an assessment
      </button>
    </div>
  )
}