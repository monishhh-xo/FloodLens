"""Transparent, deterministic rule-based flood risk prototype.

This is the engine that produces every risk number FloodLens shows for a
Chennai zone. It is *not* a trained machine-learning model - it is a documented
weighted scoring function. It is called a **Demo Risk Estimate** in the UI.

Guarantees
----------
* Deterministic: identical inputs always produce identical outputs. There is no
  randomness and no dependence on wall-clock time inside the scoring maths.
* Pure: no I/O, no global mutable state.
* Explainable: every result carries the per-factor contribution and a readable
  explanation sentence naming the top contributors.

Limitations
-----------
The control points in :mod:`app.prediction.factors` are illustrative design
assumptions. Weather-derived rainfall is real when it comes from Open-Meteo;
the terrain/drainage attributes are illustrative and are reported in a
separate bucket so the two are never conflated.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import BUCKET_ILLUSTRATIVE, BUCKET_WEATHER, RiskFactor, RiskResult
from .factors import (
    CONTROL_POINTS,
    ELEVATION_POINTS,
    RISK_SCALE_NOTE,
    WEIGHTS,
    level_for,
    piecewise,
)

ENGINE_MODE = "rule-based-demo"
ENGINE_VERSION = "0.1.0"


@dataclass(frozen=True)
class AssessInputs:
    """Fully resolved inputs for one assessment."""

    rainfall_mm_1h: float
    rainfall_mm_24h: float
    forecast_mm_next_24h: float
    drainage_capacity_index: float
    elevation_class: str
    imperviousness_pct: float
    water_proximity_m: float


# Order matters: highest weight first so the breakdown reads top-down.
_FACTOR_ORDER = (
    "rainfall_mm_1h",
    "rainfall_mm_24h",
    "forecast_24h",
    "drainage_capacity",
    "elevation_class",
    "imperviousness",
    "water_proximity",
)

_LABELS = {
    "rainfall_mm_1h": "Rainfall intensity (past hour)",
    "rainfall_mm_24h": "24-hour rainfall accumulation",
    "forecast_24h": "Forecast rainfall (next 24 h)",
    "drainage_capacity": "Drainage capacity of the zone",
    "elevation_class": "Elevation / low-lying terrain",
    "imperviousness": "Impervious surface share",
    "water_proximity": "Proximity to a water body",
}

_UNITS = {
    "rainfall_mm_1h": "mm/h",
    "rainfall_mm_24h": "mm",
    "forecast_24h": "mm",
    "drainage_capacity": "index (0-1)",
    "elevation_class": "class",
    "imperviousness": "%",
    "water_proximity": "m",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class RuleBasedPredictor:
    """Illustrative weighted-scoring flood risk prototype."""

    mode = ENGINE_MODE
    version = ENGINE_VERSION

    def assess(self, inputs: AssessInputs) -> RiskResult:
        elevation = inputs.elevation_class if inputs.elevation_class in ELEVATION_POINTS else "Mid"

        values: dict[str, float | str] = {
            "rainfall_mm_1h": _clamp(float(inputs.rainfall_mm_1h), 0.0, 300.0),
            "rainfall_mm_24h": _clamp(float(inputs.rainfall_mm_24h), 0.0, 1200.0),
            "forecast_24h": _clamp(float(inputs.forecast_mm_next_24h), 0.0, 1200.0),
            "drainage_capacity": _clamp(float(inputs.drainage_capacity_index), 0.0, 1.0),
            "elevation_class": elevation,
            "imperviousness": _clamp(float(inputs.imperviousness_pct), 0.0, 100.0),
            "water_proximity": _clamp(max(0.0, float(inputs.water_proximity_m)), 0.0, 5000.0),
        }

        raw_points: dict[str, float] = {}
        for key in _FACTOR_ORDER:
            if key == "elevation_class":
                raw_points[key] = ELEVATION_POINTS[elevation]
            else:
                raw_points[key] = piecewise(float(values[key]), CONTROL_POINTS[key])

        total = sum(raw_points.values())
        total = _clamp(total, 0.0, 100.0)
        score = round(total, 1)

        factors: list[RiskFactor] = []
        for key in _FACTOR_ORDER:
            points = round(raw_points[key], 2)
            share = round((points / total * 100.0), 1) if total > 0 else 0.0
            factors.append(
                RiskFactor(
                    key=key,
                    label=_LABELS[key],
                    bucket=BUCKET_WEATHER
                    if key in ("rainfall_mm_1h", "rainfall_mm_24h", "forecast_24h")
                    else BUCKET_ILLUSTRATIVE,
                    input_value=values[key],
                    input_unit=_UNITS[key],
                    weight_max=WEIGHTS[key],
                    points=points,
                    contribution_pct=share,
                    direction="increases" if points > 0 else "neutral",
                    note=self._note(key, values[key], points),
                )
            )

        level = level_for(score)
        return RiskResult(
            score=score,
            risk_level=level.label,
            risk_label=level.label,
            color=level.color,
            factors=tuple(factors),
            explanation=self._explain(score, level.label, factors),
            engine_mode=self.mode,
            engine_version=self.version,
        )

    # -- narrative helpers -------------------------------------------------
    @staticmethod
    def _note(key: str, value: float | str, points: float) -> str:
        if key == "rainfall_mm_1h":
            return (
                f"{float(value):.1f} mm in the past hour contributes {points:.1f} of a "
                f"possible {WEIGHTS[key]:.0f} points."
            )
        if key == "rainfall_mm_24h":
            return (
                f"{float(value):.1f} mm accumulated over 24 h contributes {points:.1f} of a "
                f"possible {WEIGHTS[key]:.0f} points."
            )
        if key == "forecast_24h":
            return (
                f"{float(value):.1f} mm forecast for the next 24 h contributes {points:.1f} of "
                f"a possible {WEIGHTS[key]:.0f} points."
            )
        if key == "drainage_capacity":
            quality = "strong" if float(value) >= 0.66 else "moderate" if float(value) >= 0.4 else "weak"
            return (
                f"Illustrative drainage capacity index {float(value):.2f} ({quality}) leaves "
                f"{points:.1f} of a possible {WEIGHTS[key]:.0f} points of unmet drainage risk."
            )
        if key == "elevation_class":
            return (
                f"Illustrative elevation class '{value}' contributes {points:.1f} of a possible "
                f"{WEIGHTS[key]:.0f} points for low-lying terrain."
            )
        if key == "imperviousness":
            return (
                f"Illustrative impervious surface share {float(value):.0f}% contributes "
                f"{points:.1f} of a possible {WEIGHTS[key]:.0f} points from surface runoff."
            )
        return (
            f"Illustrative distance of {float(value):.0f} m to the nearest mapped water body "
            f"contributes {points:.1f} of a possible {WEIGHTS[key]:.0f} points."
        )

    @staticmethod
    def _explain(score: float, level: str, factors: list[RiskFactor]) -> str:
        ranked = sorted(factors, key=lambda f: (-f.points, f.key))
        top = [f for f in ranked if f.points > 0][:3]
        weather_pts = sum(f.points for f in factors if f.bucket == BUCKET_WEATHER)
        illus_pts = sum(f.points for f in factors if f.bucket == BUCKET_ILLUSTRATIVE)

        if not top:
            head = f"Modelled risk is {score:.1f}/100 ({level}) because no factor scored above zero."
        else:
            parts = ", ".join(f"{f.label.lower()} ({f.points:.1f} pts)" for f in top)
            head = f"Modelled risk is {score:.1f}/100 ({level}). The largest contributors are {parts}."

        tail = (
            f" Weather-derived factors account for {weather_pts:.1f} points and illustrative "
            f"terrain/drainage assumptions for {illus_pts:.1f}. {RISK_SCALE_NOTE} This is a "
            f"Demo Risk Estimate, not a trained-model prediction."
        )
        return head + tail


predictor = RuleBasedPredictor()
