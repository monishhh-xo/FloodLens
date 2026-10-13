import type {
  AssessRequest,
  AssessResponse,
  HealthResponse,
  ModelInfoResponse,
  Report,
  ReportCreate,
  ReportsResponse,
  WeatherGridResponse,
  WeatherResponse,
  ZonesResponse,
} from './types'

const API_BASE: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'

export { API_BASE }

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    throw new ApiError(
      `Cannot reach the FloodLens backend at ${API_BASE}. Start it with: python -m uvicorn app.main:app --port 8000`,
      0,
    )
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status})`
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    throw new ApiError(message, response.status)
  }

  return body as T
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const serialized = search.toString()
  return serialized ? `?${serialized}` : ''
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  zones: () => request<ZonesResponse>('/api/zones'),

  assess: (payload: AssessRequest) =>
    request<AssessResponse>('/api/assess', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  weather: (latitude: number, longitude: number, refresh = false) =>
    request<WeatherResponse>(`/api/weather${query({ latitude, longitude, refresh })}`),

  weatherGrid: (refresh = false) =>
    request<WeatherGridResponse>(`/api/weather-grid${query({ refresh })}`),

  reports: (limit = 25) => request<ReportsResponse>(`/api/reports${query({ limit })}`),

  createReport: (payload: ReportCreate) =>
    request<Report>('/api/reports', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  modelInfo: () => request<ModelInfoResponse>('/api/model'),
}