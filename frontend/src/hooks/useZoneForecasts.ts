import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { WeatherResponse, Zone } from '../api/types'

/**
 * In-flight dedup: one shared promise per coordinate, so React StrictMode
 * double-mounts (and repeated renders) never duplicate the 12 requests.
 * Rejected promises are evicted so a transient failure can retry.
 */
const inflight = new Map<string, Promise<WeatherResponse>>()

function fetchZoneWeather(latitude: number, longitude: number): Promise<WeatherResponse> {
  const key = `${latitude.toFixed(5)},${longitude.toFixed(5)}`
  const existing = inflight.get(key)
  if (existing) return existing
  const promise = api.weather(latitude, longitude)
  promise.catch(() => {
    inflight.delete(key)
  })
  inflight.set(key, promise)
  return promise
}

/**
 * Fetches the live Open-Meteo rain forecast (next 24 h) for every zone so the
 * map can draw a forecast halo under each marker. Failed points stay absent —
 * the UI shows "unavailable" instead of inventing a value.
 */
export function useZoneForecasts(zones: Zone[]) {
  const [data, setData] = useState<Record<string, WeatherResponse>>({})
  const [loading, setLoading] = useState(false)
  const [allFailed, setAllFailed] = useState(false)
  const signature = zones.map((zone) => zone.id).join('|')

  useEffect(() => {
    if (zones.length === 0) return undefined
    let cancelled = false
    setLoading(true)
    setAllFailed(false)

    void Promise.allSettled(
      zones.map((zone) => fetchZoneWeather(zone.latitude, zone.longitude)),
    ).then((results) => {
      if (cancelled) return
      const next: Record<string, WeatherResponse> = {}
      let ok = 0
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          const zone = zones[index]
          if (zone) {
            next[zone.id] = result.value
            ok += 1
          }
        }
      })
      setData(next)
      setAllFailed(ok === 0)
      setLoading(false)
    })

    return () => {
      cancelled = true
    }
    // zones is captured at effect start; signature is the stable identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  return { data, loading, allFailed }
}
