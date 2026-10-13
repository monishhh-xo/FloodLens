"""Loads the trained scikit-learn artifact and exposes it honestly.

The prototype classifier was trained on 13 columns of an India-wide synthetic
dataset. This MVP collects only a subset of those columns for a Chennai zone, so
missing columns are filled with training-set statistics. The result is still
returned, because demonstrating the trained artifact end-to-end is part of the
brief - but it is **always** flagged ``reliable=False`` and never presented as a
Chennai flood probability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..config import settings
from ..ml.dataset import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES

RELIABILITY_BADGE = "Prototype - synthetic training data with no measurable signal"

CAVEAT = (
    "This probability comes from a classifier trained on a synthetic, India-wide "
    "dataset whose label is statistically independent of its features (test "
    "ROC-AUC is indistinguishable from a shuffled-label control). It is NOT a "
    "Chennai flood probability, was not validated on any real flood event, and "
    "must not be used operationally. It is shown only to demonstrate the trained "
    "artifact end to end."
)


@dataclass
class MlPrediction:
    available: bool
    probability_flood: float | None = None
    predicted_label: int | None = None
    reliable: bool = False
    badge: str = RELIABILITY_BADGE
    caveat: str = CAVEAT
    imputed_columns: list[str] = field(default_factory=list)
    inputs_used: dict = field(default_factory=dict)
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "probability_flood": self.probability_flood,
            "predicted_label": self.predicted_label,
            "reliable": self.reliable,
            "badge": self.badge,
            "caveat": self.caveat,
            "imputed_columns": self.imputed_columns,
            "inputs_used": self.inputs_used,
            "reason": self.reason,
        }


class MlPrototypePredictor:
    """Thin, defensive wrapper around the joblib artifact."""

    def __init__(
        self,
        pipeline=None,
        metadata: dict | None = None,
        reason: str | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._metadata = metadata or {}
        self._reason = reason

    # -- loading -----------------------------------------------------------
    @classmethod
    def load(cls, artifact: Path | None = None, metadata_path: Path | None = None):
        artifact = Path(artifact or settings.model_artifact)
        metadata_path = Path(metadata_path or settings.model_metadata)
        if not artifact.exists() or not metadata_path.exists():
            return cls(
                reason=(
                    "No trained model artifact found. Run "
                    "'python -m app.ml.train' in the backend directory to generate "
                    f"{artifact} and {metadata_path}."
                )
            )
        try:
            import joblib

            pipeline = joblib.load(artifact)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            return cls(reason=f"Failed to load model artifact: {exc}")
        return cls(pipeline=pipeline, metadata=metadata)

    # -- introspection -----------------------------------------------------
    @property
    def available(self) -> bool:
        return self._pipeline is not None

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    @property
    def reason(self) -> str | None:
        return self._reason

    def _impute(self, row: dict) -> tuple[dict, list[str]]:
        imputation = self._metadata.get("imputation", {})
        numeric_mean = imputation.get("numeric_mean", {})
        categorical_mode = imputation.get("categorical_mode", {})
        filled: dict = {}
        imputed: list[str] = []

        for col in NUMERIC_FEATURES:
            value = row.get(col)
            if value is None or (isinstance(value, float) and pd.isna(value)):
                filled[col] = float(numeric_mean.get(col, 0.0))
                imputed.append(col)
            else:
                filled[col] = float(value)

        for col in CATEGORICAL_FEATURES:
            value = row.get(col)
            if value is None:
                filled[col] = str(categorical_mode.get(col, "Urban"))
                imputed.append(col)
            else:
                filled[col] = str(value)

        return filled, imputed

    # -- prediction --------------------------------------------------------
    def predict(self, feature_row: dict) -> MlPrediction:
        if not self.available:
            return MlPrediction(available=False, reason=self._reason)

        filled, imputed = self._impute(feature_row)
        frame = pd.DataFrame([{col: filled[col] for col in FEATURES}])
        probability = float(self._pipeline.predict_proba(frame)[0, 1])
        return MlPrediction(
            available=True,
            probability_flood=round(probability, 4),
            predicted_label=int(probability >= 0.5),
            reliable=False,
            imputed_columns=sorted(imputed),
            inputs_used=filled,
        )

    def predict_many(self, rows: list[dict]) -> list[float]:
        """Batch prediction used to verify the artifact against held-out rows."""
        if not self.available or not rows:
            return []
        frame = pd.DataFrame([{col: r[col] for col in FEATURES} for r in rows])
        return [round(float(p), 4) for p in self._pipeline.predict_proba(frame)[:, 1]]
