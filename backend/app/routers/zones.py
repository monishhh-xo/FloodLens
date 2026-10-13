"""GET /api/zones

Returns the curated Chennai zone catalogue with a live-computed baseline risk
preview. The preview is produced by the same engine that serves /api/assess, so
the dashboard never shows a hard-coded number.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..config import DISCLAIMER
from ..prediction.factors import BASELINE_PREVIEW_RAINFALL, RISK_SCALE_NOTE
from ..prediction.registry import get_rule_predictor
from ..prediction.rule_based import AssessInputs
from ..schemas import FactorOut, RiskPreview, Zone, ZonesResponse
from ..services.zone_catalog import ILLUSTRATIVE_NOTE, ZONES

router = APIRouter(tags=["zones"])

BASELINE_NOTE = (
    "Illustrative preview computed with a documented assumed rainfall input "
    f"({BASELINE_PREVIEW_RAINFALL['rainfall_mm_1h']:.0f} mm/1 h, "
    f"{BASELINE_PREVIEW_RAINFALL['rainfall_mm_24h']:.0f} mm/24 h). Not a live reading."
)


def baseline_preview(zone) -> RiskPreview:
    predictor = get_rule_predictor()
    result = predictor.assess(
        AssessInputs(
            rainfall_mm_1h=BASELINE_PREVIEW_RAINFALL["rainfall_mm_1h"],
            rainfall_mm_24h=BASELINE_PREVIEW_RAINFALL["rainfall_mm_24h"],
            forecast_mm_next_24h=BASELINE_PREVIEW_RAINFALL["forecast_mm_next_24h"],
            drainage_capacity_index=zone.drainage_capacity_index,
            elevation_class=zone.elevation_class,
            imperviousness_pct=zone.imperviousness_pct,
            water_proximity_m=zone.water_proximity_m,
        )
    )
    top_factors = [FactorOut(**f.to_dict()) for f in result.factors]
    return RiskPreview(
        score=result.score,
        risk_level=result.risk_level,
        color=result.color,
        assumed_rainfall_mm_1h=BASELINE_PREVIEW_RAINFALL["rainfall_mm_1h"],
        assumed_rainfall_mm_24h=BASELINE_PREVIEW_RAINFALL["rainfall_mm_24h"],
        assumed_forecast_mm_next_24h=BASELINE_PREVIEW_RAINFALL["forecast_mm_next_24h"],
        illustrative=True,
        note=BASELINE_NOTE,
        top_factors=top_factors,
    )


@router.get("/zones", response_model=ZonesResponse, summary="Chennai demo zones")
def list_zones() -> ZonesResponse:
    zones = []
    for zone in ZONES:
        payload = zone.to_dict()
        payload["baseline_demo_risk"] = baseline_preview(zone)
        zones.append(Zone(**payload))

    return ZonesResponse(
        count=len(zones),
        focus_city="Chennai, Tamil Nadu, India",
        coordinate_source=(
            "OpenStreetMap place coordinates resolved via Nominatim "
            "(approximate locality centroids)."
        ),
        attributes_illustrative=True,
        illustrative_note=f"{ILLUSTRATIVE_NOTE} {RISK_SCALE_NOTE}",
        disclaimer=DISCLAIMER,
        zones=zones,
    )
