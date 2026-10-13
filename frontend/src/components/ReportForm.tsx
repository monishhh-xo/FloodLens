import { useState } from 'react'
import type { Report, Severity, Zone } from '../api/types'
import { api } from '../api/client'
import { ErrorState, PrimaryButton } from './ui'

export default function ReportForm({
  zones,
  onCreated,
}: {
  zones: Zone[]
  onCreated: (report: Report) => void
}) {
  const [zoneId, setZoneId] = useState<string>(zones[0]?.id ?? '')
  const [latitude, setLatitude] = useState<string>(zones[0] ? String(zones[0].latitude) : '')
  const [longitude, setLongitude] = useState<string>(zones[0] ? String(zones[0].longitude) : '')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState<Severity>('Moderate')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  function applyZone(id: string) {
    setZoneId(id)
    const zone = zones.find((z) => z.id === id)
    if (zone) {
      setLatitude(String(zone.latitude))
      setLongitude(String(zone.longitude))
    }
  }

  async function submit() {
    setError(null)
    setSuccess(null)
    const lat = Number(latitude)
    const lon = Number(longitude)
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      setError('Enter a valid latitude between -90 and 90.')
      return
    }
    if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
      setError('Enter a valid longitude between -180 and 180.')
      return
    }
    setSubmitting(true)
    try {
      const created = await api.createReport({
        zone_id: zoneId,
        zone_name: zones.find((z) => z.id === zoneId)?.name ?? null,
        latitude: lat,
        longitude: lon,
        description,
        severity,
      })
      setSuccess(`Report recorded as id ${created.id.slice(0, 8)}… (unverified, user-submitted).`)
      setDescription('')
      onCreated(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  const inputCls =
    'w-full px-3 py-2 rounded-md border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500'

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-500 leading-snug">
        Community-submitted waterlogging observations. Reports are stored locally and always marked
        as <strong>unverified, user-submitted</strong>. No name, phone or other personal details are
        requested.
      </p>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Nearest zone</label>
        <select value={zoneId} onChange={(event) => applyZone(event.target.value)} className={inputCls}>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Latitude</label>
          <input
            type="number"
            step="any"
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Longitude</label>
          <input
            type="number"
            step="any"
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
            className={inputCls}
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Description of what you observed (5–600 characters)
        </label>
        <textarea
          rows={3}
          maxLength={600}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="e.g. Water entered shops near the junction; drains overflowing."
          className={inputCls}
        />
        <p className="text-[11px] text-slate-400 mt-0.5 text-right">{description.length}/600</p>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Severity</label>
        <select value={severity} onChange={(event) => setSeverity(event.target.value as Severity)} className={inputCls}>
          {(['Low', 'Moderate', 'High', 'Severe'] as const).map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </div>

      {error && <ErrorState title="Could not submit report" message={error} onRetry={() => submit()} />}
      {success && (
        <p className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          {success}
        </p>
      )}

      <PrimaryButton onClick={submit} loading={submitting} disabled={submitting}>
        Submit report
      </PrimaryButton>
    </div>
  )
}