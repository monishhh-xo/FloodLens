"""Runtime configuration for the FloodLens AI backend.

Values are read from environment variables when present so the app can be
relocated without code changes, but every value has a safe local default.
Deliberately dependency-free (no pydantic-settings) to keep the MVP install
surface small and the failure modes obvious.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


class Settings:
    """Application settings. Instantiate once at import time."""

    app_name = "FloodLens AI API"
    app_description = (
        "AI-based urban flood hotspot predictor (hackathon MVP). "
        "Not an official flood-warning system."
    )
    version = "0.1.0"

    # The transparent rule engine that actually produces Chennai risk estimates.
    engine_mode = "rule-based-demo"
    engine_version = "0.1.0"

    # CORS is restricted to the local Vite dev server only.
    allowed_origins: list[str] = _env_list(
        "FLOODLENS_ALLOWED_ORIGINS",
        ["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    dataset_path: Path = _env_path(
        "FLOODLENS_DATASET", PROJECT_ROOT / "data" / "flood_risk_dataset_india.csv"
    )
    models_dir: Path = _env_path("FLOODLENS_MODELS_DIR", BACKEND_DIR / "models")
    var_dir: Path = _env_path("FLOODLENS_VAR_DIR", BACKEND_DIR / "var")

    model_artifact: Path = models_dir / "flood_model.joblib"
    model_metadata: Path = models_dir / "model_metadata.json"
    model_metrics: Path = models_dir / "model_metrics.json"

    database_path: Path = var_dir / "reports.sqlite3"

    # --- Open-Meteo -------------------------------------------------------
    weather_base_url = "https://api.open-meteo.com/v1/forecast"
    weather_source_label = "Open-Meteo (api.open-meteo.com), free public forecast API"
    weather_timeout_s: float = _env_float("FLOODLENS_WEATHER_TIMEOUT", 8.0)
    weather_cache_ttl_s: int = _env_int("FLOODLENS_WEATHER_CACHE_TTL", 600)
    weather_forecast_days: int = 2
    timezone = "Asia/Kolkata"

    # --- reports ----------------------------------------------------------
    max_reports_returned: int = 200
    max_report_description_len = 600


settings = Settings()

DISCLAIMER = (
    "FloodLens AI is a hackathon prototype for demonstration and education. "
    "It is NOT an official flood-warning system and must not be used for "
    "emergency decisions. Always follow official advisories from your local "
    "disaster-management authority."
)

ILLUSTRATIVE_WARNING = (
    "Illustrative demo data only. These values are documented assumptions, not "
    "surveyed measurements, and the mapped points are not verified flood hotspots."
)
