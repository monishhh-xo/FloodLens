"""Gridded weather for the Windy-style map (Chennai bbox).

Open-Meteo supports multi-location requests: comma-separated latitude/longitude
lists are paired index-wise. A small grid (5x5 = 25 points) around Chennai
costs exactly **one** upstream HTTP call and returns a JSON array.

Failure contract matches :mod:`app.services.weather_client`: any upstream
problem returns ``available=False`` plus a human-readable reason and **no
numeric series at all** - the map falls back to the plain base map rather than
drawing fabricated weather.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from ..config import settings

ROWS = 5
COLS = 5
FORECAST_DAYS = 2

# Chennai bounding box used for the weather grid.
GRID_BOUNDS: dict[str, float] = {
    "south": 12.85,
    "west": 80.05,
    "north": 13.25,
    "east": 80.35,
}

HOURLY_FIELDS: tuple[str, ...] = (
    "wind_speed_10m",
    "wind_direction_10m",
    "temperature_2m",
    "precipitation",
    "cloud_cover",
)

UNITS: dict[str, str] = {
    "wind_speed": "km/h",
    "wind_direction": "deg (direction the wind blows FROM)",
    "temperature": "\u00b0C",
    "precipitation": "mm",
    "cloud_cover": "%",
}

ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_S = 600
CACHE_KEY = "chennai-grid-5x5"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_grid_points() -> tuple[list[float], list[float], list[tuple[float, float]]]:
    """Uniform lat/lon grid over the Chennai bbox, row-major points."""
    south, north = GRID_BOUNDS["south"], GRID_BOUNDS["north"]
    west, east = GRID_BOUNDS["west"], GRID_BOUNDS["east"]
    lats = [south + i * (north - south) / (ROWS - 1) for i in range(ROWS)]
    lons = [west + j * (east - west) / (COLS - 1) for j in range(COLS)]
    points = [(lat, lon) for lat in lats for lon in lons]
    return lats, lons, points


def _unavailable(reason: str) -> dict:
    return {
        "available": False,
        "status": "unavailable",
        "source": settings.weather_source_label,
        "attribution": ATTRIBUTION,
        "retrieved_at_utc": None,
        "timezone": None,
        "units": None,
        "grid": {
            "rows": ROWS,
            "cols": COLS,
            "bounds": dict(GRID_BOUNDS),
            "points_requested": ROWS * COLS,
        },
        "hours": [],
        "series": {},
        "stats": {},
        "reason": reason,
        "notes": [
            "No gridded weather is returned while the upstream API is unreachable. "
            "The map falls back to the base map only; nothing is interpolated or invented."
        ],
        "cache": {"hit": False, "ttl_seconds": CACHE_TTL_S},
    }


def _round(value, digits: int = 1):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


async def fetch_weather_grid(*, refresh: bool = False) -> dict:
    now = time.monotonic()
    if not refresh:
        cached = _cache.get(CACHE_KEY)
        if cached and cached[0] > now:
            payload = dict(cached[1])
            payload["cache"] = {
                "hit": True,
                "ttl_seconds": CACHE_TTL_S,
                "expires_in_seconds": round(cached[0] - now, 1),
            }
            return payload

    lats, lons, points = build_grid_points()
    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": settings.timezone,
        "forecast_days": FORECAST_DAYS,
    }

    source = settings.weather_source_label
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(settings.weather_base_url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return _unavailable(
            f"Open-Meteo did not respond within 30s for the {ROWS * COLS}-point grid."
        )
    except httpx.HTTPStatusError as exc:
        return _unavailable(f"Open-Meteo returned HTTP {exc.response.status_code} for the grid.")
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return _unavailable(
            f"Could not read the Open-Meteo grid response ({type(exc).__name__})."
        )

    locations = data if isinstance(data, list) else [data]
    if len(locations) != ROWS * COLS:
        return _unavailable(
            f"Open-Meteo returned {len(locations)} grid points; expected {ROWS * COLS}."
        )

    first_hourly = locations[0].get("hourly") or {}
    hours = first_hourly.get("time") or []
    if not hours:
        return _unavailable("Open-Meteo responded but the grid payload had no hourly series.")

    n_hours = len(hours)
    # series[field][hour][row][col]
    series: dict[str, list[list[list[float | None]]]] = {
        field: [ [[None] * COLS for _ in range(ROWS)] for _ in range(n_hours) ]
        for field in HOURLY_FIELDS
    }

    digits = {"wind_direction_10m": 0, "cloud_cover": 0, "precipitation": 2}

    for index, location in enumerate(locations):
        row, col = divmod(index, COLS)
        hourly = location.get("hourly") or {}
        for field in HOURLY_FIELDS:
            values = hourly.get(field) or []
            bucket = series[field]
            for hour_index in range(min(n_hours, len(values))):
                bucket[hour_index][row][col] = _round(
                    values[hour_index], digits.get(field, 1)
                )

    # Per-hour min/max across the grid so the UI can label its legend honestly.
    stats: dict[str, list[dict[str, float]]] = {}
    for field in HOURLY_FIELDS:
        field_stats: list[dict[str, float]] = []
        for hour_index in range(n_hours):
            flat = [
                value
                for row_values in series[field][hour_index]
                for value in row_values
                if value is not None
            ]
            if flat:
                field_stats.append(
                    {"min": _round(min(flat), 1), "max": _round(max(flat), 1)}
                )
            else:
                field_stats.append({"min": 0.0, "max": 0.0})
        stats[field] = field_stats

    payload = {
        "available": True,
        "status": "ok",
        "source": source,
        "attribution": ATTRIBUTION,
        "retrieved_at_utc": _now_iso(),
        "timezone": locations[0].get("timezone") or settings.timezone,
        "units": dict(UNITS),
        "grid": {
            "rows": ROWS,
            "cols": COLS,
            "lats": [round(lat, 4) for lat in lats],
            "lons": [round(lon, 4) for lon in lons],
            "bounds": dict(GRID_BOUNDS),
            "points_requested": ROWS * COLS,
        },
        "hours": hours,
        "series": series,
        "stats": stats,
        "reason": None,
        "notes": [
            "Gridded forecast for the Chennai bounding box; values are forecast "
            "fields, not measurements from local instruments.",
            "Wind direction is the direction the wind blows FROM (meteorological "
            "convention); the map animates motion in the opposite direction.",
        ],
        "cache": {"hit": False, "ttl_seconds": CACHE_TTL_S},
    }

    _cache[CACHE_KEY] = (now + CACHE_TTL_S, payload)
    return payload


def cache_info() -> dict:
    now = time.monotonic()
    live = sum(1 for expires, _ in _cache.values() if expires > now)
    return {"entries": len(_cache), "live_entries": live, "ttl_seconds": CACHE_TTL_S}


def clear_cache() -> None:
    _cache.clear()
