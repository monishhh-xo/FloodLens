import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { WeatherResponse } from '../api/types'

/**
 * Fetches live Open-Meteo weather for a point. Pass null coordinates to pause
 * fetching (e.g. while a map popup is still closed), so no request is made
 * until the user actually opens it.
 */
export function useZoneWeather(
  latitude: number | null,
  longitude: number | null,
) {
  const [weather, setWeather] = useState<WeatherResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(
    async (refresh: boolean) => {
      if (latitude === null || longitude === null) return
      setLoading(true)
      setError(null)
      try {
        const data = await api.weather(latitude, longitude, refresh)
        setWeather(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    },
    [latitude, longitude],
  )

  useEffect(() => {
    if (latitude !== null && longitude !== null) {
      void load(false)
    }
  }, [latitude, longitude, load])

  return {
    weather,
    loading,
    error,
    refresh: () => load(true),
  }
}