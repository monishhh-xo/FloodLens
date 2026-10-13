"""Shared contract for FloodLens prediction engines.

Any engine - the transparent rule prototype or a future trained model - returns
a :class:`RiskResult` describing the score, a labelled risk band, and the
per-factor explanation behind that score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Buckets keep weather-derived evidence separate from illustrative assumptions.
BUCKET_WEATHER = "weather"
BUCKET_ILLUSTRATIVE = "illustrative"


@dataclass(frozen=True)
class RiskFactor:
    """One contributing factor behind a risk score."""

    key: str
    label: str
    bucket: str  # BUCKET_WEATHER | BUCKET_ILLUSTRATIVE
    input_value: float | str
    input_unit: str
    weight_max: float
    points: float
    contribution_pct: float
    direction: str  # "increases" | "neutral"
    note: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "bucket": self.bucket,
            "input_value": self.input_value,
            "input_unit": self.input_unit,
            "weight_max": self.weight_max,
            "points": self.points,
            "contribution_pct": self.contribution_pct,
            "direction": self.direction,
            "note": self.note,
        }


@dataclass(frozen=True)
class RiskResult:
    """Deterministic output of a prediction engine."""

    score: float
    risk_level: str
    risk_label: str
    color: str
    factors: tuple[RiskFactor, ...]
    explanation: str
    engine_mode: str
    engine_version: str

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "risk_level": self.risk_level,
            "risk_label": self.risk_label,
            "color": self.color,
            "factors": [f.to_dict() for f in self.factors],
            "explanation": self.explanation,
            "engine_mode": self.engine_mode,
            "engine_version": self.engine_version,
        }


@runtime_checkable
class Predictor(Protocol):
    """Interface a replacement engine must satisfy."""

    mode: str
    version: str

    def assess(self, inputs) -> RiskResult:  # pragma: no cover - protocol
        ...
