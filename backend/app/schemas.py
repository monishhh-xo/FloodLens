"""Pydantic request/response models.

Request models are strict: unknown fields are rejected (``extra="forbid"``) so
typos surface as 422s instead of silently ignored input.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["Low", "Moderate", "High", "Severe"]
RainfallSource = Literal["manual", "open-meteo-forecast", "illustrative-defaults"]


# --------------------------------------------------------------------------
# health
# --------------------------------------------------------------------------
class PredictorStatus(BaseModel):
    mode: str
    version: str
    label: str
    trained_ml_used_for_risk: bool


class MlArtifactStatus(BaseModel):
    available: bool
    artifact_loaded: bool
    reliable: bool
    reason: str | None = None


class DatabaseStatus(BaseModel):
    ok: bool
    path: str
    reports_count: int | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    server_time_utc: str
    predictor: PredictorStatus
    ml_artifact: MlArtifactStatus
    weather: dict[str, Any]
    database: DatabaseStatus
    disclaimer: str


# --------------------------------------------------------------------------
# zones
# --------------------------------------------------------------------------
class FactorOut(BaseModel):
    key: str
    label: str
    bucket: Literal["weather", "illustrative"]
    input_value: float | str
    input_unit: str
    weight_max: float
    points: float
    contribution_pct: float
    direction: Literal["increases", "neutral"]
    note: str


class RiskPreview(BaseModel):
    score: float
    risk_level: str
    color: str
    assumed_rainfall_mm_1h: float
    assumed_rainfall_mm_24h: float
    assumed_forecast_mm_next_24h: float
    illustrative: bool
    note: str
    top_factors: list[FactorOut] = Field(default_factory=list)


class Zone(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    land_cover: str
    soil_type: str
    imperviousness_pct: float
    drainage_capacity_index: float
    elevation_class: str
    water_proximity_m: float
    infrastructure_index: int
    historical_flood_flag: int
    descriptive_note: str
    attributes_illustrative: bool
    illustrative_note: str
    baseline_demo_risk: RiskPreview | None = None


class ZonesResponse(BaseModel):
    count: int
    focus_city: str
    coordinate_source: str
    attributes_illustrative: bool
    illustrative_note: str
    disclaimer: str
    zones: list[Zone]


# --------------------------------------------------------------------------
# assessment
# --------------------------------------------------------------------------
class AssessRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "zone_id": "velachery",
                    "rainfall_mm_1h": 45.0,
                    "rainfall_mm_24h": 190.0,
                    "forecast_mm_next_24h": 95.0,
                }
            ]
        },
    )

    zone_id: str | None = Field(
        default=None, description="A zone id from GET /api/zones."
    )
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)

    rainfall_mm_1h: float | None = Field(
        default=None, ge=0.0, le=300.0, description="Rainfall in the past hour, mm."
    )
    rainfall_mm_24h: float | None = Field(
        default=None, ge=0.0, le=1200.0, description="Rolling 24-hour rainfall, mm."
    )
    forecast_mm_next_24h: float | None = Field(
        default=None, ge=0.0, le=1200.0, description="Forecast rainfall next 24 h, mm."
    )

    rainfall_source: RainfallSource | None = Field(
        default=None,
        description=(
            "Where the rainfall figures came from. If omitted and no rainfall is "
            "supplied, the server tries Open-Meteo."
        ),
    )
    allow_illustrative_fallback: bool = Field(
        default=False,
        description=(
            "Opt in to documented illustrative rainfall defaults when live weather "
            "is unavailable. Those defaults are clearly labelled in the response."
        ),
    )


class RiskEstimate(BaseModel):
    score: float = Field(ge=0, le=100)
    risk_level: Severity
    risk_label: Severity
    color: str
    factors: list[FactorOut]
    explanation: str
    engine_mode: str
    engine_version: str
    kind: Literal["Demo Risk Estimate"] = "Demo Risk Estimate"
    is_trained_model: bool = False


class MlPrototypeOut(BaseModel):
    available: bool
    probability_flood: float | None = None
    predicted_label: int | None = None
    reliable: bool = False
    badge: str
    caveat: str
    imputed_columns: list[str] = Field(default_factory=list)
    inputs_used: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    is_trained_model: bool = True
    trained_on: str = "synthetic India-wide dataset with no measurable signal"


class DataQuality(BaseModel):
    rainfall_source: str
    weather_available: bool
    rainfall_is_live_forecast: bool
    illustrative_inputs_used: bool
    resolved_zone: str
    notes: list[str]


class AssessResponse(BaseModel):
    assessment_id: str
    computed_at_utc: str
    zone: Zone
    rule_estimate: RiskEstimate
    ml_prototype: MlPrototypeOut
    inputs: dict[str, Any]
    data_quality: DataQuality
    risk_scale_note: str
    disclaimer: str


# --------------------------------------------------------------------------
# weather
# --------------------------------------------------------------------------
class WeatherResponse(BaseModel):
    available: bool
    status: str
    source: str
    attribution: str
    retrieved_at_utc: str | None = None
    timezone: str | None = None
    units: dict[str, Any] | None = None
    requested: dict[str, float]
    resolved: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    hourly: list[dict[str, Any]] = Field(default_factory=list)
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    cache: dict[str, Any]


class WeatherGridResponse(BaseModel):
    """Gridded forecast for the Windy-style map.

    ``series[field]`` is ``[hour][row][col]``; empty when unavailable.
    """

    available: bool
    status: str
    source: str
    attribution: str
    retrieved_at_utc: str | None = None
    timezone: str | None = None
    units: dict[str, str] | None = None
    grid: dict[str, Any] = Field(default_factory=dict)
    hours: list[str] = Field(default_factory=list)
    series: dict[str, list[list[list[float | None]]]] = Field(default_factory=dict)
    stats: dict[str, list[dict[str, float]]] = Field(default_factory=dict)
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    cache: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------
class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    description: str = Field(
        ...,
        min_length=5,
        max_length=600,
        description="What you observed on the ground. Do not include personal information.",
    )
    severity: Severity
    zone_id: str | None = None
    zone_name: str | None = None


class Report(BaseModel):
    id: str
    created_at_utc: str
    zone_id: str | None
    zone_name: str | None
    latitude: float
    longitude: float
    description: str
    severity: Severity
    source: str
    verification: str


class ReportsResponse(BaseModel):
    count: int
    source: str
    note: str
    reports: list[Report]
