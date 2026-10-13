"""GET /api/health"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..config import DISCLAIMER, settings
from ..prediction.registry import get_ml_predictor
from ..schemas import (
    DatabaseStatus,
    HealthResponse,
    MlArtifactStatus,
    PredictorStatus,
)
from ..services import reports_store, weather_client

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health() -> HealthResponse:
    ml = get_ml_predictor()
    database = reports_store.health()

    db_status = DatabaseStatus(
        ok=bool(database.get("ok")),
        path=str(database.get("path")),
        reports_count=database.get("reports_count"),
        error=database.get("error"),
    )

    status = "ok" if db_status.ok else "degraded"

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.version,
        server_time_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        predictor=PredictorStatus(
            mode=settings.engine_mode,
            version=settings.engine_version,
            label="Transparent rule-based Demo Risk Estimate",
            trained_ml_used_for_risk=False,
        ),
        ml_artifact=MlArtifactStatus(
            available=ml.available,
            artifact_loaded=ml.available,
            reliable=False,
            reason=ml.reason,
        ),
        weather={
            "configured": True,
            "provider": "Open-Meteo",
            "cache": weather_client.cache_info(),
        },
        database=db_status,
        disclaimer=DISCLAIMER,
    )
