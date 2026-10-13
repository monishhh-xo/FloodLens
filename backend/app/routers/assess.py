"""POST /api/assess

Produces one assessment containing two clearly separated outputs:

* ``rule_estimate`` - the transparent Demo Risk Estimate that drives the UI.
* ``ml_prototype``  - the trained scikit-learn artifact, always flagged
  ``reliable=false``, shown only to demonstrate the artifact end to end.

Rainfall resolution order: caller-supplied figures win; otherwise the live
Open-Meteo forecast is used; otherwise documented illustrative defaults are used
*only* when the caller explicitly opts in. If none of those apply the request is
rejected with 422 - the API never silently invents a rainfall value.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..config import DISCLAIMER
from ..prediction.factors import (
    ILLUSTRATIVE_RAINFALL_DEFAULTS,
    RISK_SCALE_NOTE,
)
from ..prediction.registry import get_ml_predictor, get_rule_predictor
from ..prediction.rule_based import AssessInputs
from ..schemas import (
    AssessRequest,
    AssessResponse,
    DataQuality,
    MlPrototypeOut,
    RiskEstimate,
    Zone,
)
from ..services.weather_client import fetch_weather
from ..services.zone_catalog import (
    ZONES_BY_ID,
    custom_zone,
    get_zone,
    nearest_zone,
)

router = APIRouter(tags=["assessment"])

NEAREST_ZONE_MAX_KM = 3.0


def _resolve_zone(payload: AssessRequest) -> tuple[object, str, list[str]]:
    notes: list[str] = []

    if payload.zone_id:
        zone = get_zone(payload.zone_id)
        if zone is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Unknown zone_id {payload.zone_id!r}. Valid ids: "
                    f"{sorted(ZONES_BY_ID)}."
                ),
            )
        return zone, f"catalogued zone '{zone.id}'", notes

    if payload.latitude is None or payload.longitude is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Provide either 'zone_id', or both 'latitude' and 'longitude' "
                "to run an assessment."
            ),
        )

    match = nearest_zone(payload.latitude, payload.longitude, max_km=NEAREST_ZONE_MAX_KM)
    if match is not None:
        zone, distance = match
        notes.append(
            f"Coordinates snapped to the nearest catalogued zone ({zone.name}), "
            f"{distance:.2f} km away."
        )
        return zone, f"nearest zone '{zone.id}' ({distance:.2f} km)", notes

    zone = custom_zone(payload.latitude, payload.longitude)
    notes.append(
        f"No catalogued zone within {NEAREST_ZONE_MAX_KM:.0f} km; illustrative "
        f"catalogue-average attributes were applied to your coordinates."
    )
    return zone, "user-supplied coordinates", notes


@router.post("/assess", response_model=AssessResponse, summary="Run a flood risk assessment")
async def assess(payload: AssessRequest) -> AssessResponse:
    zone, resolved_zone_label, notes = _resolve_zone(payload)

    # Always attempt live weather: it supplies rainfall when the caller omitted
    # it, and temperature/humidity for the prototype model when they did not.
    weather = await fetch_weather(zone.latitude, zone.longitude)
    weather_available = bool(weather.get("available"))
    if weather_available:
        notes.append(
            f"Live weather retrieved from Open-Meteo at {weather['retrieved_at_utc']} "
            f"(source: {weather['source']})."
        )
    else:
        notes.append(f"Live weather unavailable: {weather.get('reason')}")

    rainfall_mm_1h = payload.rainfall_mm_1h
    rainfall_mm_24h = payload.rainfall_mm_24h
    forecast_mm_next_24h = payload.forecast_mm_next_24h
    rainfall_source = payload.rainfall_source or "manual"
    illustrative_inputs_used = False

    if rainfall_mm_1h is None and rainfall_mm_24h is None:
        if weather_available:
            summary = weather["summary"]
            rainfall_mm_1h = summary["current_precipitation_mm"]
            rainfall_mm_24h = summary["next_24h_precipitation_mm"]
            forecast_mm_next_24h = summary["next_24h_precipitation_mm"]
            rainfall_source = "open-meteo-forecast"
            notes.append(
                "No rainfall was supplied, so the live Open-Meteo forecast was used. "
                "The 24-hour figure is a forecast total, not an observed accumulation."
            )
        elif payload.allow_illustrative_fallback:
            rainfall_mm_1h = ILLUSTRATIVE_RAINFALL_DEFAULTS["rainfall_mm_1h"]
            rainfall_mm_24h = ILLUSTRATIVE_RAINFALL_DEFAULTS["rainfall_mm_24h"]
            forecast_mm_next_24h = ILLUSTRATIVE_RAINFALL_DEFAULTS["forecast_mm_next_24h"]
            rainfall_source = "illustrative-defaults"
            illustrative_inputs_used = True
            notes.append(
                "Live weather was unavailable and allow_illustrative_fallback=true, so "
                "documented illustrative rainfall defaults were used. These are NOT live "
                "or observed readings."
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Live weather is unavailable "
                    f"({weather.get('reason')}). Supply 'rainfall_mm_1h' and/or "
                    "'rainfall_mm_24h' explicitly, or set "
                    "'allow_illustrative_fallback': true to use clearly-labelled "
                    "illustrative defaults. No rainfall value is ever invented silently."
                ),
            )

    if rainfall_mm_1h is None:
        rainfall_mm_1h = 0.0
        notes.append("rainfall_mm_1h was not supplied and is treated as 0.0 mm.")
    if rainfall_mm_24h is None:
        rainfall_mm_24h = 0.0
        notes.append("rainfall_mm_24h was not supplied and is treated as 0.0 mm.")
    if forecast_mm_next_24h is None:
        forecast_mm_next_24h = 0.0
        notes.append("forecast_mm_next_24h was not supplied and is treated as 0.0 mm.")

    rainfall_is_live = rainfall_source == "open-meteo-forecast"

    # -- rule engine -------------------------------------------------------
    rule = get_rule_predictor().assess(
        AssessInputs(
            rainfall_mm_1h=rainfall_mm_1h,
            rainfall_mm_24h=rainfall_mm_24h,
            forecast_mm_next_24h=forecast_mm_next_24h,
            drainage_capacity_index=zone.drainage_capacity_index,
            elevation_class=zone.elevation_class,
            imperviousness_pct=zone.imperviousness_pct,
            water_proximity_m=zone.water_proximity_m,
        )
    )

    # -- prototype model ---------------------------------------------------
    current = (weather.get("current") or {}) if weather_available else {}
    ml_row = {
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "rainfall_mm": rainfall_mm_24h,
        "temperature_c": current.get("temperature_c"),
        "humidity_pct": current.get("relative_humidity_pct"),
        # Not collected by this MVP -> imputed with training-set statistics.
        "river_discharge_m3s": None,
        "water_level_m": None,
        "elevation_m": None,
        "population_density": None,
        "infrastructure": zone.infrastructure_index,
        "historical_floods": zone.historical_flood_flag,
        "land_cover": zone.land_cover,
        "soil_type": zone.soil_type,
    }
    ml_prediction = get_ml_predictor().predict(ml_row)
    ml_out = MlPrototypeOut(**ml_prediction.to_dict())
    if ml_out.available and ml_out.imputed_columns:
        ml_out.reason = (
            "Columns not collected by this MVP were imputed with training-set "
            f"statistics: {', '.join(ml_out.imputed_columns)}."
        )

    zone_payload = zone.to_dict()
    from .zones import baseline_preview  # local import avoids a circular import

    zone_payload["baseline_demo_risk"] = baseline_preview(zone)

    return AssessResponse(
        assessment_id=uuid.uuid4().hex,
        computed_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        zone=Zone(**zone_payload),
        rule_estimate=RiskEstimate(**rule.to_dict()),
        ml_prototype=ml_out,
        inputs={
            "weather_derived": {
                "rainfall_mm_1h": round(float(rainfall_mm_1h), 2),
                "rainfall_mm_24h": round(float(rainfall_mm_24h), 2),
                "forecast_mm_next_24h": round(float(forecast_mm_next_24h), 2),
                "temperature_c": current.get("temperature_c"),
                "relative_humidity_pct": current.get("relative_humidity_pct"),
                "source": rainfall_source,
                "is_live_forecast": rainfall_is_live,
            },
            "illustrative_zone_attributes": {
                "drainage_capacity_index": zone.drainage_capacity_index,
                "elevation_class": zone.elevation_class,
                "imperviousness_pct": zone.imperviousness_pct,
                "water_proximity_m": zone.water_proximity_m,
                "land_cover": zone.land_cover,
                "soil_type": zone.soil_type,
                "infrastructure_index": zone.infrastructure_index,
                "historical_flood_flag_illustrative_only": zone.historical_flood_flag,
                "attributes_illustrative": True,
            },
        },
        data_quality=DataQuality(
            rainfall_source=rainfall_source,
            weather_available=weather_available,
            rainfall_is_live_forecast=rainfall_is_live,
            illustrative_inputs_used=illustrative_inputs_used or rainfall_source == "manual",
            resolved_zone=resolved_zone_label,
            notes=notes,
        ),
        risk_scale_note=RISK_SCALE_NOTE,
        disclaimer=DISCLAIMER,
    )
