"""Shared pytest fixtures.

Reports are redirected to a temporary SQLite file per test so the suite never
touches the developer's local database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.main import app
    from app.services import reports_store

    monkeypatch.setattr(reports_store, "_DB_PATH", tmp_path / "test_reports.sqlite3")
    reports_store.init_db()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def offline_weather(monkeypatch):
    """Force every weather lookup to report the upstream API as unavailable."""

    async def _unavailable(*args, **kwargs):
        return {
            "available": False,
            "status": "unavailable",
            "source": "Open-Meteo (api.open-meteo.com), free public forecast API",
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
            "retrieved_at_utc": None,
            "timezone": None,
            "units": None,
            "requested": {"latitude": 0.0, "longitude": 0.0},
            "resolved": None,
            "current": None,
            "summary": None,
            "hourly": [],
            "reason": "Simulated upstream outage for testing.",
            "notes": [],
            "cache": {"hit": False, "ttl_seconds": 0},
        }

    import app.routers.assess as assess_router
    import app.routers.weather as weather_router

    monkeypatch.setattr(assess_router, "fetch_weather", _unavailable)
    monkeypatch.setattr(weather_router, "fetch_weather", _unavailable)


@pytest.fixture()
def online_weather(monkeypatch):
    """Deterministic fake weather payload so tests never hit the network."""

    payload = {
        "available": True,
        "status": "ok",
        "source": "Open-Meteo (api.open-meteo.com), free public forecast API",
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
        "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
        "timezone": "Asia/Kolkata",
        "units": {"precipitation": "mm", "temperature": "\u00b0C"},
        "requested": {"latitude": 12.98, "longitude": 80.22},
        "resolved": {"latitude": 12.98, "longitude": 80.22, "elevation_m": 6.0},
        "current": {
            "time": "2026-01-01T00:00",
            "precipitation_mm": 4.5,
            "temperature_c": 29.0,
            "relative_humidity_pct": 78.0,
        },
        "summary": {
            "current_precipitation_mm": 4.5,
            "next_24h_precipitation_mm": 55.0,
            "next_24h_peak_hourly_mm": 12.0,
            "next_24h_peak_hour": "2026-01-01T05:00",
            "next_24h_max_probability_pct": 80,
            "hours_covered": 24,
        },
        "hourly": [],
        "reason": None,
        "notes": [],
        "cache": {"hit": False, "ttl_seconds": 600},
    }

    async def _ok(*args, **kwargs):
        return dict(payload)

    import app.routers.assess as assess_router
    import app.routers.weather as weather_router

    monkeypatch.setattr(assess_router, "fetch_weather", _ok)
    monkeypatch.setattr(weather_router, "fetch_weather", _ok)
