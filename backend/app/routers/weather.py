"""GET /api/weather

Proxies Open-Meteo. When the upstream call fails the endpoint still returns 200
with ``available=false`` and a ``reason`` - the request itself succeeded in
reporting the data-availability state, and the frontend renders that as an
offline/demo banner. No numeric value is ever invented on failure.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas import WeatherResponse
from ..services.weather_client import fetch_weather

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherResponse, summary="Live rainfall forecast")
async def weather(
    latitude: float = Query(
        ..., ge=-90.0, le=90.0, description="Latitude in decimal degrees."
    ),
    longitude: float = Query(
        ..., ge=-180.0, le=180.0, description="Longitude in decimal degrees."
    ),
    refresh: bool = Query(
        default=False, description="Bypass the short-lived server-side cache."
    ),
) -> WeatherResponse:
    payload = await fetch_weather(latitude, longitude, use_cache=not refresh)
    return WeatherResponse(**payload)
