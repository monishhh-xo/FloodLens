"""Documented scoring control points for the FloodLens rule engine.

Every number in this module is an **illustrative design assumption**, not a
surveyed measurement and not an official warning threshold. They are declared
here, in one place, so that the scoring is fully auditable and reproducible.

Scoring model
-------------
Each factor maps an observed/assumed input onto a point allowance via
piecewise-linear interpolation between the control points below. The factor
point allowances sum to 100, so ``score`` is already a 0-100 scale.

Factor weights (maximum points):

    rainfall_mm_1h       30   weather-derived
    rainfall_mm_24h      25   weather-derived
    forecast_24h         15   weather-derived
    drainage_capacity    10   illustrative zone attribute
    elevation_class      10   illustrative zone attribute
    imperviousness        6   illustrative zone attribute
    water_proximity       4   illustrative zone attribute
                        ----
                        100
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLevel:
    key: str
    label: str
    color: str
    min_score: float
    max_score: float  # exclusive upper bound, except for the top band


RISK_LEVELS: tuple[RiskLevel, ...] = (
    RiskLevel("low", "Low", "#16a34a", 0.0, 25.0),
    RiskLevel("moderate", "Moderate", "#d97706", 25.0, 50.0),
    RiskLevel("high", "High", "#ea580c", 50.0, 75.0),
    RiskLevel("severe", "Severe", "#dc2626", 75.0, 100.01),
)

RISK_SCALE_NOTE = (
    "Risk bands are illustrative prototype thresholds (Low 0-24, Moderate 25-49, "
    "High 50-74, Severe 75-100) and are not an official flood-warning scale."
)


def level_for(score: float) -> RiskLevel:
    """Map a 0-100 score onto a labelled risk band."""
    clamped = max(0.0, min(100.0, float(score)))
    for level in RISK_LEVELS:
        if clamped < level.max_score:
            return level
    return RISK_LEVELS[-1]


# --- control points: (input, points) ---------------------------------------
# Lines are monotonic; y may decrease when a larger input means lower risk
# (better drainage capacity, greater distance from a water body).

CONTROL_POINTS: dict[str, tuple[tuple[float, float], ...]] = {
    # Hourly rainfall intensity, mm/h.
    "rainfall_mm_1h": ((0.0, 0.0), (15.0, 15.0), (30.0, 24.0), (60.0, 30.0)),
    # Rolling 24-hour rainfall accumulation, mm.
    "rainfall_mm_24h": ((0.0, 0.0), (50.0, 8.0), (100.0, 16.0), (200.0, 25.0)),
    # Forecast rainfall for the next 24 hours, mm.
    "forecast_24h": ((0.0, 0.0), (50.0, 6.0), (150.0, 15.0)),
    # Zone drainage capacity index, 0 (none) - 1 (excellent). Higher = safer.
    "drainage_capacity": ((0.0, 10.0), (0.5, 5.0), (1.0, 0.0)),
    # Impervious surface share, %. Higher = more runoff.
    "imperviousness": ((0.0, 0.0), (50.0, 3.0), (100.0, 6.0)),
    # Distance to nearest mapped water body, m. Higher = safer.
    "water_proximity": ((0.0, 4.0), (500.0, 2.0), (1000.0, 0.0)),
}

WEIGHTS: dict[str, float] = {
    "rainfall_mm_1h": 30.0,
    "rainfall_mm_24h": 25.0,
    "forecast_24h": 15.0,
    "drainage_capacity": 10.0,
    "elevation_class": 10.0,
    "imperviousness": 6.0,
    "water_proximity": 4.0,
}

ELEVATION_POINTS: dict[str, float] = {"High": 0.0, "Mid": 4.0, "Low": 10.0}

# Documented fallback used ONLY when the caller explicitly opts in via
# ``allow_illustrative_fallback=true``. Never presented as live observation.
ILLUSTRATIVE_RAINFALL_DEFAULTS: dict[str, float] = {
    "rainfall_mm_1h": 12.0,
    "rainfall_mm_24h": 75.0,
    "forecast_mm_next_24h": 60.0,
}

# Same fallback rainfall applied to every zone when computing the published
# baseline preview on GET /api/zones. Labelled illustrative in the response.
BASELINE_PREVIEW_RAINFALL: dict[str, float] = {
    "rainfall_mm_1h": 12.0,
    "rainfall_mm_24h": 75.0,
    "forecast_mm_next_24h": 60.0,
}


def piecewise(value: float, points: tuple[tuple[float, float], ...]) -> float:
    """Interpolate ``value`` across ``points`` (clamped outside the range)."""
    pts = sorted(points)
    if value <= pts[0][0]:
        return pts[0][1]
    if value >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y1
            t = (value - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]
