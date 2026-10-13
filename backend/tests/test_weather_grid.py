from __future__ import annotations

ROWS = COLS = 5
N_HOURS = 48


def _fake_grid(**overrides) -> dict:
    hours = [f"2026-10-13T{h % 24:02d}:00" for h in range(N_HOURS)]
    series = {
        field: [[[float(h + i + j) for j in range(COLS)] for i in range(ROWS)] for h in range(N_HOURS)]
        for field in (
            "wind_speed_10m",
            "wind_direction_10m",
            "temperature_2m",
            "precipitation",
            "cloud_cover",
        )
    }
    payload = {
        "available": True,
        "status": "ok",
        "source": "Open-Meteo (api.open-meteo.com), free public forecast API",
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
        "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
        "timezone": "Asia/Kolkata",
        "units": {"wind_speed": "km/h", "temperature": "\u00b0C", "precipitation": "mm"},
        "grid": {
            "rows": ROWS,
            "cols": COLS,
            "lats": [12.85 + i * 0.05 for i in range(ROWS)],
            "lons": [80.05 + j * 0.0375 for j in range(COLS)],
            "bounds": {"south": 12.85, "west": 80.05, "north": 13.25, "east": 80.35},
            "points_requested": ROWS * COLS,
        },
        "hours": hours,
        "series": series,
        "stats": {
            field: [{"min": 0.0, "max": 50.0} for _ in range(N_HOURS)] for field in series
        },
        "reason": None,
        "notes": [],
        "cache": {"hit": False, "ttl_seconds": 600},
    }
    payload.update(overrides)
    return payload


import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def grid_client(monkeypatch, tmp_path):
    from app.main import app
    from app.services import reports_store
    import app.routers.weather_grid as weather_grid_router

    async def _ok(*args, **kwargs):
        return _fake_grid()

    # The router binds the service function at import time, so patch the name
    # the route actually calls (hermetic: no real network access in tests).
    monkeypatch.setattr(weather_grid_router, "fetch_weather_grid", _ok)
    monkeypatch.setattr(reports_store, "_DB_PATH", tmp_path / "grid_test.sqlite3")
    reports_store.init_db()
    with TestClient(app) as client:
        yield client


def test_weather_grid_success_shape(grid_client):
    response = grid_client.get("/api/weather-grid")
    assert response.status_code == 200
    body = response.json()

    assert body["available"] is True
    assert body["grid"]["rows"] == ROWS
    assert body["grid"]["cols"] == COLS
    assert body["grid"]["points_requested"] == ROWS * COLS
    assert len(body["hours"]) == N_HOURS
    assert body["units"]["wind_speed"] == "km/h"
    assert "Open-Meteo" in body["source"]

    for field in ("wind_speed_10m", "wind_direction_10m", "temperature_2m", "precipitation", "cloud_cover"):
        series = body["series"][field]
        assert len(series) == N_HOURS
        assert len(series[0]) == ROWS
        assert len(series[0][0]) == COLS
        assert len(body["stats"][field]) == N_HOURS


def test_weather_grid_offline_contains_no_series(monkeypatch, tmp_path):
    from app.main import app
    from app.services import reports_store
    import app.routers.weather_grid as weather_grid_router

    async def _down(*args, **kwargs):
        return {
            "available": False,
            "status": "unavailable",
            "source": "Open-Meteo",
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
            "retrieved_at_utc": None,
            "timezone": None,
            "units": None,
            "grid": {"rows": ROWS, "cols": COLS},
            "hours": [],
            "series": {},
            "stats": {},
            "reason": "Simulated grid outage.",
            "notes": [],
            "cache": {"hit": False, "ttl_seconds": 0},
        }

    monkeypatch.setattr(weather_grid_router, "fetch_weather_grid", _down)
    monkeypatch.setattr(reports_store, "_DB_PATH", tmp_path / "grid_offline.sqlite3")
    reports_store.init_db()

    with TestClient(app) as client:
        body = client.get("/api/weather-grid").json()

    assert body["available"] is False
    assert body["reason"] == "Simulated grid outage."
    assert body["series"] == {}
    assert body["hours"] == []
    assert body["units"] is None
    assert body["retrieved_at_utc"] is None


def test_build_grid_points_is_uniform_and_inside_bbox():
    from app.services.weather_grid import GRID_BOUNDS, build_grid_points

    lats, lons, points = build_grid_points()
    assert len(points) == ROWS * COLS
    assert len(lats) == ROWS and len(lons) == COLS

    lat_steps = {round(lats[i + 1] - lats[i], 6) for i in range(ROWS - 1)}
    lon_steps = {round(lons[j + 1] - lons[j], 6) for j in range(COLS - 1)}
    assert len(lat_steps) == 1
    assert len(lon_steps) == 1

    for lat, lon in points:
        assert GRID_BOUNDS["south"] <= lat <= GRID_BOUNDS["north"]
        assert GRID_BOUNDS["west"] <= lon <= GRID_BOUNDS["east"]


def test_health_still_reports_ok_with_grid_route(grid_client):
    body = grid_client.get("/api/health").json()
    assert body["status"] in ("ok", "degraded")
