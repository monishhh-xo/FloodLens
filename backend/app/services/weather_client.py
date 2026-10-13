"""Open-Meteo weather client with explicit failure states.

Contract: when the upstream call fails for any reason, this module returns
``available=False`` plus a human-readable ``reason`` and **no numeric fields at
all**. It never fabricates, estimates or carries forward a rainfall value.

Retrieved values are cached briefly (default 600 s) keyed on the rounded
coordinates, and every payload reports the source, the units and the UTC
retrieval time so the UI can attribute them.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from ..config import settings

_cache: dict[tuple[float, float], tuple[float, dict]] = {}

ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"

_CURRENT_FIELDS = "precipitation,temperature_2m,relative_humidity_2m"
_HOURLY_FIELDS = "precipitation,precipitation_probability"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _unavailable(reason: str, latitude: float, longitude: float, source: str) -> dict:
    return {
        "available": False,
        "status": "unavailable",
        "source": source,
        "attribution": ATTRIBUTION,
        "retrieved_at_utc": None,
        "timezone": None,
        "units": None,
        "requested": {"latitude": latitude, "longitude": longitude},
        "resolved": None,
        "current": None,
        "summary": None,
        "hourly": [],
        "reason": reason,
        "notes": [
            "No live weather values are returned while the upstream API is "
            "unreachable. Nothing is estimated or substituted."
        ],
        "cache": {"hit": False, "ttl_seconds": settings.weather_cache_ttl_s},
    }


def _slice_next_24h(times: list[str], values: list, current_time: str) -> tuple[list, int]:
    if not times:
        return [], 0
    current_hour = current_time[:13] + ":00"
    start = 0
    for index, stamp in enumerate(times):
        if stamp >= current_hour:
            start = index
            break
    window = list(range(start, min(start + 24, len(times))))
    return window, start


async def fetch_weather(latitude: float, longitude: float, *, use_cache: bool = True) -> dict:
    key = (round(float(latitude), 3), round(float(longitude), 3))
    now = time.monotonic()

    if use_cache:
        cached = _cache.get(key)
        if cached and cached[0] > now:
            payload = dict(cached[1])
            payload["cache"] = {
                "hit": True,
                "ttl_seconds": settings.weather_cache_ttl_s,
                "expires_in_seconds": round(cached[0] - now, 1),
            }
            return payload

    params = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "current": _CURRENT_FIELDS,
        "hourly": _HOURLY_FIELDS,
        "timezone": settings.timezone,
        "forecast_days": settings.weather_forecast_days,
    }

    source = settings.weather_source_label
    try:
        async with httpx.AsyncClient(timeout=settings.weather_timeout_s) as client:
            response = await client.get(settings.weather_base_url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return _unavailable(
            f"Open-Meteo did not respond within {settings.weather_timeout_s:.0f}s.",
            latitude,
            longitude,
            source,
        )
    except httpx.HTTPStatusError as exc:
        return _unavailable(
            f"Open-Meteo returned HTTP {exc.response.status_code}.",
            latitude,
            longitude,
            source,
        )
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return _unavailable(
            f"Could not read the Open-Meteo response ({type(exc).__name__}).",
            latitude,
            longitude,
            source,
        )

    hourly = data.get("hourly") or {}
    hourly_units = data.get("hourly_units") or {}
    current = data.get("current") or {}
    times = hourly.get("time") or []

    if not times or not current:
        return _unavailable(
            "Open-Meteo responded but the payload contained no hourly series.",
            latitude,
            longitude,
            source,
        )

    precip_units = hourly_units.get("precipitation")
    if precip_units != "mm":
        return _unavailable(
            f"Unexpected precipitation units from Open-Meteo: {precip_units!r}.",
            latitude,
            longitude,
            source,
        )

    current_time = str(current.get("time") or times[0])
    window, _ = _slice_next_24h(times, hourly.get("precipitation") or [], current_time)

    hourly_series = []
    for index in window:
        hourly_series.append(
            {
                "time": times[index],
                "precipitation_mm": _as_float((hourly.get("precipitation") or [None] * len(times))[index]),
                "precipitation_probability_pct": _as_float(
                    (hourly.get("precipitation_probability") or [None] * len(times))[index]
                ),
            }
        )

    precip_values = [h["precipitation_mm"] for h in hourly_series if h["precipitation_mm"] is not None]
    prob_values = [
        h["precipitation_probability_pct"]
        for h in hourly_series
        if h["precipitation_probability_pct"] is not None
    ]

    peak_value = max(precip_values) if precip_values else 0.0
    peak_hour = next(
        (h["time"] for h in hourly_series if h["precipitation_mm"] == peak_value), None
    )

    payload = {
        "available": True,
        "status": "ok",
        "source": source,
        "attribution": ATTRIBUTION,
        "retrieved_at_utc": _now_iso(),
        "timezone": data.get("timezone") or settings.timezone,
        "units": {
            "precipitation": precip_units,
            "temperature": (data.get("current_units") or {}).get("temperature_2m", "\u00b0C"),
            "relative_humidity": (data.get("current_units") or {}).get("relative_humidity_2m", "%"),
            "precipitation_probability": hourly_units.get("precipitation_probability", "%"),
        },
        "requested": {"latitude": float(latitude), "longitude": float(longitude)},
        "resolved": {
            "latitude": _as_float(data.get("latitude")),
            "longitude": _as_float(data.get("longitude")),
            "elevation_m": _as_float(data.get("elevation")),
        },
        "current": {
            "time": current_time,
            "precipitation_mm": _as_float(current.get("precipitation")),
            "temperature_c": _as_float(current.get("temperature_2m")),
            "relative_humidity_pct": _as_float(current.get("relative_humidity_2m")),
        },
        "summary": {
            "current_precipitation_mm": _as_float(current.get("precipitation")),
            "next_24h_precipitation_mm": round(sum(precip_values), 2) if precip_values else 0.0,
            "next_24h_peak_hourly_mm": round(peak_value, 2),
            "next_24h_peak_hour": peak_hour,
            "next_24h_max_probability_pct": max(prob_values) if prob_values else None,
            "hours_covered": len(hourly_series),
        },
        "hourly": hourly_series,
        "reason": None,
        "notes": [
            "Values are the Open-Meteo forecast for the requested coordinates, "
            "not observations from a local rain gauge.",
            "\"current_precipitation_mm\" is the precipitation of the current hour.",
        ],
        "cache": {"hit": False, "ttl_seconds": settings.weather_cache_ttl_s},
    }

    _cache[key] = (now + settings.weather_cache_ttl_s, payload)
    return payload


def _as_float(value) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def cache_info() -> dict:
    now = time.monotonic()
    live = sum(1 for expires, _ in _cache.values() if expires > now)
    return {"entries": len(_cache), "live_entries": live, "ttl_seconds": settings.weather_cache_ttl_s}


def clear_cache() -> None:
    _cache.clear()
