// Shared API types mirroring the FastAPI schemas.

export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe'
export type Severity = RiskLevel

export interface RiskFactor {
  key: string
  label: string
  bucket: 'weather' | 'illustrative'
  input_value: number | string
  input_unit: string
  weight_max: number
  points: number
  contribution_pct: number
  direction: 'increases' | 'neutral'
  note: string
}

export interface RiskEstimate {
  score: number
  risk_level: RiskLevel
  risk_label: RiskLevel
  color: string
  factors: RiskFactor[]
  explanation: string
  engine_mode: string
  engine_version: string
  kind: 'Demo Risk Estimate'
  is_trained_model: false
}

export interface MlPrototype {
  available: boolean
  probability_flood: number | null
  predicted_label: number | null
  reliable: boolean
  badge: string
  caveat: string
  imputed_columns: string[]
  inputs_used: Record<string, unknown>
  reason: string | null
  is_trained_model: boolean
  trained_on: string
}

export interface RiskPreview {
  score: number
  risk_level: RiskLevel
  color: string
  assumed_rainfall_mm_1h: number
  assumed_rainfall_mm_24h: number
  assumed_forecast_mm_next_24h: number
  illustrative: boolean
  note: string
  top_factors: RiskFactor[]
}

export interface Zone {
  id: string
  name: string
  latitude: number
  longitude: number
  land_cover: string
  soil_type: string
  imperviousness_pct: number
  drainage_capacity_index: number
  elevation_class: string
  water_proximity_m: number
  infrastructure_index: number
  historical_flood_flag: number
  descriptive_note: string
  attributes_illustrative: boolean
  illustrative_note: string
  baseline_demo_risk: RiskPreview | null
}

export interface ZonesResponse {
  count: number
  focus_city: string
  coordinate_source: string
  attributes_illustrative: boolean
  illustrative_note: string
  disclaimer: string
  zones: Zone[]
}

export interface DataQuality {
  rainfall_source: string
  weather_available: boolean
  rainfall_is_live_forecast: boolean
  illustrative_inputs_used: boolean
  resolved_zone: string
  notes: string[]
}

export interface AssessResponse {
  assessment_id: string
  computed_at_utc: string
  zone: Zone
  rule_estimate: RiskEstimate
  ml_prototype: MlPrototype
  inputs: {
    weather_derived: Record<string, unknown>
    illustrative_zone_attributes: Record<string, unknown>
  }
  data_quality: DataQuality
  risk_scale_note: string
  disclaimer: string
}

export interface AssessRequest {
  zone_id?: string | null
  latitude?: number | null
  longitude?: number | null
  rainfall_mm_1h?: number | null
  rainfall_mm_24h?: number | null
  forecast_mm_next_24h?: number | null
  rainfall_source?: 'manual' | 'open-meteo-forecast' | 'illustrative-defaults' | null
  allow_illustrative_fallback?: boolean
}

export interface WeatherCurrent {
  time: string
  precipitation_mm: number | null
  temperature_c: number | null
  relative_humidity_pct: number | null
}

export interface WeatherSummary {
  current_precipitation_mm: number | null
  next_24h_precipitation_mm: number
  next_24h_peak_hourly_mm: number
  next_24h_peak_hour: string | null
  next_24h_max_probability_pct: number | null
  hours_covered: number
}

export interface WeatherResponse {
  available: boolean
  status: string
  source: string
  attribution: string
  retrieved_at_utc: string | null
  timezone: string | null
  units: Record<string, string> | null
  requested: { latitude: number; longitude: number }
  resolved: { latitude: number; longitude: number; elevation_m: number | null } | null
  current: WeatherCurrent | null
  summary: WeatherSummary | null
  hourly: Array<{
    time: string
    precipitation_mm: number | null
    precipitation_probability_pct: number | null
  }>
  reason: string | null
  notes: string[]
  cache: { hit: boolean; ttl_seconds: number }
}

export type WeatherGridField =
  | 'wind_speed_10m'
  | 'wind_direction_10m'
  | 'temperature_2m'
  | 'precipitation'
  | 'cloud_cover'

export interface WeatherGridResponse {
  available: boolean
  status: string
  source: string
  attribution: string
  retrieved_at_utc: string | null
  timezone: string | null
  units: Record<string, string> | null
  grid: {
    rows: number
    cols: number
    lats?: number[]
    lons?: number[]
    bounds: { south: number; west: number; north: number; east: number }
    points_requested: number
  }
  hours: string[]
  /** series[field][hour][row][col] */
  series: Partial<Record<WeatherGridField, Array<Array<Array<number | null>>>>>
  stats: Partial<Record<WeatherGridField, Array<{ min: number; max: number }>>>
  reason: string | null
  notes: string[]
  cache: { hit: boolean; ttl_seconds: number; expires_in_seconds?: number }
}

export interface Report {
  id: string
  created_at_utc: string
  zone_id: string | null
  zone_name: string | null
  latitude: number
  longitude: number
  description: string
  severity: Severity
  source: string
  verification: string
}

export interface ReportsResponse {
  count: number
  source: string
  note: string
  reports: Report[]
}

export interface ReportCreate {
  zone_id?: string | null
  zone_name?: string | null
  latitude: number
  longitude: number
  description: string
  severity: Severity
}

export interface HealthResponse {
  status: string
  service: string
  version: string
  server_time_utc: string
  predictor: {
    mode: string
    version: string
    label: string
    trained_ml_used_for_risk: boolean
  }
  ml_artifact: { available: boolean; artifact_loaded: boolean; reliable: boolean; reason: string | null }
  weather: Record<string, unknown>
  database: { ok: boolean; path: string; reports_count: number | null; error: string | null }
  disclaimer: string
}

export interface ModelInfoResponse {
  prototype: boolean
  reliable: boolean
  is_trained_model: boolean
  used_for_live_risk_estimates: boolean
  warning: string
  model_name: string
  model_version: string
  algorithm: string
  trained_at_utc: string
  dataset_integrity: {
    rows: number
    columns: number
    sha256: string
    target_counts: Record<string, number>
    target_balance: Record<string, number>
    null_values: number
    duplicate_rows: number
    column_names: string[]
    provenance: string
  }
  metrics: {
    logistic_regression: {
      train: MetricsRow
      test: MetricsRow
    }
    random_forest_comparison: {
      train: MetricsRow
      test: MetricsRow
    }
    majority_class_baseline: { strategy: string; accuracy: number; positive_rate_in_test: number }
    shuffled_label_control: {
      seed: number
      roc_auc_vs_true_labels: number
      accuracy_vs_true_labels: number
      note: string
    }
    univariate_feature_signal: {
      numeric: Array<{ feature: string; kind: string; auc: number; distance_from_chance: number }>
      categorical: Array<{ feature: string; kind: string; levels: unknown[]; flood_rate_spread: number }>
    }
    verdict: {
      signal_detected: boolean
      test_auc: number
      auc_above_chance: number
      control_auc: number
      margin_over_control: number
      accuracy_improvement_over_baseline: number
      summary: string
    }
  }
  artifact_check: {
    available: boolean
    sampled_rows: Array<{
      latitude: number
      longitude: number
      rainfall_mm: number
      actual_label: number
      predicted_probability: number | null
    }>
    note: string
    reason?: string
  }
  limitations: string[]
  environment: Record<string, string>
  note: string
}

export interface MetricsRow {
  n: number
  accuracy: number
  precision: number
  recall: number
  f1: number
  roc_auc: number
  confusion_matrix: {
    labels: string[]
    true_negative: number
    false_positive: number
    false_negative: number
    true_positive: number
  }
}