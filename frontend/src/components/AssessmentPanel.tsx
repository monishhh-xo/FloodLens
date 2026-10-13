import { useEffect, useState } from 'react'
import type { AssessResponse, Zone } from '../api/types'
import { api } from '../api/client'
import { formatNumber, levelOf } from '../lib/format'
import { Badge, ErrorState, PrimaryButton, RiskBadge, ScoreBar } from './ui'
import FactorBreakdown from './FactorBreakdown'

interface AssessmentPanelProps {
  zones: Zone[]
  selectedZoneId: string | null
  onSelectZone: (id: string) => void
  onAssessmentComplete: (result: AssessResponse) => void
}

function toNum(raw: string): number | null {
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}

export default function AssessmentPanel({
  zones,
  selectedZoneId,
  onSelectZone,
  onAssessmentComplete,
}: AssessmentPanelProps) {
  const [zoneId, setZoneId] = useState<string>(selectedZoneId ?? zones[0]?.id ?? '')
  const [rain1h, setRain1h] = useState('')
  const [rain24h, setRain24h] = useState('')
  const [forecast, setForecast] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AssessResponse | null>(null)

  // When a zone is picked on the map/detail panel, adopt it here and prefill
  // its documented baseline assumed rainfall so the button is never a no-op.
  useEffect(() => {
    if (selectedZoneId && selectedZoneId !== zoneId) {
      const zone = zones.find((z) => z.id === selectedZoneId)
      setZoneId(selectedZoneId)
      if (zone?.baseline_demo_risk) {
        const preview = zone.baseline_demo_risk
        setRain1h(String(preview.assumed_rainfall_mm_1h))
        setRain24h(String(preview.assumed_rainfall_mm_24h))
        setForecast(String(preview.assumed_forecast_mm_next_24h))
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedZoneId])

  const selected = zones.find((z) => z.id === zoneId) ?? null

  async function runAssessment() {
    setError(null)
    setRunning(true)
    try {
      const hasRainfall = zoneId && (rain1h.trim() !== '' || rain24h.trim() !== '')
      const response = await api.assess({
        zone_id: hasRainfall ? zoneId : null,
        latitude: selected?.latitude,
        longitude: selected?.longitude,
        rainfall_mm_1h: rain1h.trim() !== '' ? toNum(rain1h) : null,
        rainfall_mm_24h: rain24h.trim() !== '' ? toNum(rain24h) : null,
        forecast_mm_next_24h: forecast.trim() !== '' ? toNum(forecast) : null,
        rainfall_source: 'manual',
        allow_illustrative_fallback: true,
      })
      setResult(response)
      onAssessmentComplete(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRunning(false)
    }
  }

  const inputCls =
    'w-full px-3 py-2 rounded-md border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500'

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Zone</label>
        <select
          value={zoneId}
          onChange={(event) => {
            setZoneId(event.target.value)
            onSelectZone(event.target.value)
          }}
          className={inputCls}
        >
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
          <option value="custom">User-supplied coordinates (not catalogued)</option>
        </select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Rainfall — past hour (mm)
          </label>
          <input
            type="number"
            min={0}
            max={300}
            step="0.1"
            placeholder="e.g. 45"
            value={rain1h}
            onChange={(event) => setRain1h(event.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Rainfall — 24 hours (mm)
          </label>
          <input
            type="number"
            min={0}
            max={1200}
            step="0.1"
            placeholder="e.g. 190"
            value={rain24h}
            onChange={(event) => setRain24h(event.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Forecast — next 24 h (mm, optional)
          </label>
          <input
            type="number"
            min={0}
            max={1200}
            step="0.1"
            placeholder="e.g. 95"
            value={forecast}
            onChange={(event) => setForecast(event.target.value)}
            className={inputCls}
          />
        </div>
      </div>

      <p className="text-[11px] text-slate-500 leading-snug">
        Leave rainfall fields empty to pull the live Open-Meteo forecast for the selected zone. If
        weather is down and no rainfall is entered, documented <em>illustrative defaults</em> are
        used and labelled as such — never invented live data.
      </p>

      {error && <ErrorState title="Assessment failed" message={error} onRetry={() => runAssessment()} />}

      <div className="flex items-center gap-3">
        <PrimaryButton onClick={runAssessment} loading={running} disabled={running || !selected}>
          Run Assessment
        </PrimaryButton>
        <Badge tone="amber">Demo Risk Estimate</Badge>
      </div>

      {result && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div>
              <p className="text-xs text-slate-500">
                Assessment for <strong className="text-slate-800">{result.zone.name}</strong> ·{' '}
                {result.data_quality.rainfall_source.replaceAll('-', ' ')}
              </p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-3xl font-black text-slate-900">
                  {formatNumber(result.rule_estimate.score)}
                </span>
                <span className="text-slate-400 text-sm">/100</span>
                <RiskBadge level={result.rule_estimate.risk_level} />
              </div>
            </div>
            <div className="text-right text-[11px] text-slate-500">
              <p>{levelOf(result.rule_estimate.score)} rainfall-driven score</p>
              <p>
                live forecast:{' '}
                {result.data_quality.rainfall_is_live_forecast ? 'yes' : 'no'}
              </p>
            </div>
          </div>

          <ScoreBar score={result.rule_estimate.score} color={result.rule_estimate.color} />

          <div>
            <p className="text-sm font-medium text-slate-800 mb-2">What factors drive this estimate</p>
            <FactorBreakdown factors={result.rule_estimate.factors} />
          </div>

          <div className="rounded-md bg-white border border-slate-200 p-3">
            <p className="text-xs text-slate-700 leading-relaxed">{result.rule_estimate.explanation}</p>
          </div>

          {result.data_quality.notes.length > 0 && (
            <ul className="text-[11px] text-slate-600 space-y-1">
              {result.data_quality.notes.map((note, index) => (
                <li key={index} className="flex gap-1.5">
                  <span className="text-slate-400">•</span>
                  {note}
                </li>
              ))}
            </ul>
          )}

          {result.ml_prototype.available ? (
            <div className="rounded-md border border-purple-200 bg-purple-50 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="red">ML prototype — NOT reliable</Badge>
                <span className="text-sm font-semibold text-purple-900">
                  P(flood) = {formatNumber(result.ml_prototype.probability_flood, 3)}
                </span>
              </div>
              <p className="text-[11px] text-purple-800 mt-1.5 leading-snug">
                {result.ml_prototype.caveat}
              </p>
              {result.ml_prototype.imputed_columns.length > 0 && (
                <p className="text-[11px] text-purple-700 mt-1">
                  Imputed columns: {result.ml_prototype.imputed_columns.join(', ')}.
                </p>
              )}
              {result.ml_prototype.reason && (
                <p className="text-[11px] text-purple-700 mt-1">{result.ml_prototype.reason}</p>
              )}
            </div>
          ) : (
            <div className="rounded-md border border-slate-200 bg-white p-3">
              <p className="text-[11px] text-slate-500">
                ML prototype unavailable: {result.ml_prototype.reason}
              </p>
            </div>
          )}

          <p className="text-[10px] text-slate-400 leading-snug">{result.disclaimer}</p>
        </div>
      )}
    </div>
  )
}