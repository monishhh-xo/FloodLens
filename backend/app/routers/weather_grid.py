"""GET /api/weather-grid

Gridded Open-Meteo forecast (5x5 points over the Chennai bounding box) in a
single upstream call, used by the Windy-style animated map for wind particles
and rain/temperature/cloud layers.

Failure contract: the endpoint still returns 200 with ``available=false`` and a
``reason`` so the map can show an honest offline state instead of fabricating a
weather field.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas import WeatherGridResponse
from ..services.weather_grid import fetch_weather_grid

router = APIRouter(tags=["weather"])


@router.get(
    "/weather-grid",
    response_model=WeatherGridResponse,
    summary="Gridded rainfall/wind/temperature/cloud forecast for the map",
)
async def weather_grid(
    refresh: bool = Query(default=False, description="Bypass the server-side cache."),
) -> WeatherGridResponse:
    payload = await fetch_weather_grid(refresh=refresh)
    return WeatherGridResponse(**payload)
