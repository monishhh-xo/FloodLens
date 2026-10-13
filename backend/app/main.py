"""FloodLens AI - FastAPI application factory.

Run from the ``backend`` directory::

    python -m uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import DISCLAIMER, settings
from .routers import assess, health, model_info, reports, weather, weather_grid, zones
from .services import reports_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    reports_store.init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.version,
    lifespan=lifespan,
)

# CORS is restricted to the local Vite dev server only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a readable 422 body instead of FastAPI's raw error dump."""
    safe_errors = json.loads(json.dumps(exc.errors(), default=str))
    messages = []
    for error in safe_errors:
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        messages.append(f"{location or 'body'}: {error.get('msg', 'invalid value')}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed.",
            "errors": messages,
            "raw": safe_errors,
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(zones.router, prefix="/api")
app.include_router(assess.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(weather_grid.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(model_info.router, prefix="/api")


@app.get("/", tags=["system"], summary="Service banner")
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "focus_city": "Chennai, Tamil Nadu, India",
        "endpoints": [
            "GET /api/health",
            "GET /api/zones",
            "POST /api/assess",
            "GET /api/weather?latitude=..&longitude=..",
            "GET /api/reports",
            "POST /api/reports",
            "GET /api/model",
        ],
        "disclaimer": DISCLAIMER,
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
