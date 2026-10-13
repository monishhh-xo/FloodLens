"""GET /api/reports and POST /api/reports

Community waterlogging reports. Stored locally in SQLite, always marked
``source: user-submitted`` and ``verification: unverified``. No personal data is
collected: the request model deliberately has no name/email/phone field.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ..config import settings
from ..schemas import Report, ReportCreate, ReportsResponse
from ..services import reports_store
from ..services.zone_catalog import get_zone

router = APIRouter(tags=["reports"])

NOTE = (
    "These are unverified community submissions stored locally for demonstration. "
    "They are not official incident records and must not be treated as confirmed "
    "flood events."
)


@router.get("/reports", response_model=ReportsResponse, summary="Recent community reports")
def list_reports(
    limit: int = Query(default=25, ge=1, le=settings.max_reports_returned),
    zone_id: str | None = Query(default=None, description="Filter to one zone id."),
) -> ReportsResponse:
    reports = reports_store.list_reports(limit=limit, zone_id=zone_id)
    return ReportsResponse(
        count=len(reports),
        source="user-submitted",
        note=NOTE,
        reports=[Report(**r) for r in reports],
    )


@router.post(
    "/reports",
    response_model=Report,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a community report",
)
def create_report(payload: ReportCreate) -> Report:
    zone_name = payload.zone_name
    zone_id = payload.zone_id

    if zone_id:
        zone = get_zone(zone_id)
        if zone is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown zone_id {zone_id!r}. Omit it or use an id from GET /api/zones.",
            )
        zone_name = zone_name or zone.name

    description = payload.description.strip()
    if len(description) < 5:
        raise HTTPException(
            status_code=422,
            detail="Description must contain at least 5 characters after trimming.",
        )

    record = reports_store.create_report(
        latitude=payload.latitude,
        longitude=payload.longitude,
        description=description,
        severity=payload.severity,
        zone_id=zone_id,
        zone_name=zone_name,
    )
    return Report(**record)
