import type { HealthResponse, WeatherResponse } from '../api/types'

export default function StatusBanner({
  health,
  healthError,
  weather,
}: {
  health: HealthResponse | null
  healthError: string | null
  weather: WeatherResponse | null
}) {
  if (healthError && !health) {
    return (
      <div className="mx-4 md:mx-6 mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
        <strong>Backend unreachable.</strong> {healthError}
        <div className="mt-1 text-xs text-red-700">
          Start it with <code className="bg-red-100 px-1 rounded">cd backend; python -m uvicorn app.main:app --port 8000</code>
        </div>
      </div>
    )
  }

  if (weather && !weather.available) {
    return (
      <div className="mx-4 md:mx-6 mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>Weather API unavailable — running in offline/demo state.</strong>
        <p className="mt-0.5 text-xs text-amber-800">
          {weather.reason ?? 'The upstream service could not be reached.'} No live rainfall is being
          displayed or substituted. You can still run assessments with rainfall you enter manually.
        </p>
      </div>
    )
  }

  return null
}