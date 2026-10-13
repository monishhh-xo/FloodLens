"""GET /api/model

Exposes the trained prototype and its real evaluation results, including the
controls that show it learned nothing useful. Also re-verifies dataset integrity
at request time, so the "10,000 rows x 14 columns" claim is checked against the
actual file rather than asserted from a README.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..ml.dataset import FEATURES, TARGET, load_validated
from ..prediction.registry import get_ml_predictor

router = APIRouter(tags=["model"])

_artifact_check_cache: dict | None = None


def _load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _artifact_check() -> dict:
    """Run the saved artifact on held-out synthetic rows.

    Reproduces the training split parameters exactly, so the sampled rows were
    not used to fit the model.
    """
    global _artifact_check_cache
    if _artifact_check_cache is not None:
        return _artifact_check_cache

    meta_path = Path(settings.model_metadata)
    if not meta_path.exists():
        _artifact_check_cache = {"available": False, "reason": "No model metadata found."}
        return _artifact_check_cache

    metadata = _load_json(meta_path)
    predictor = get_ml_predictor()
    if not predictor.available:
        _artifact_check_cache = {"available": False, "reason": predictor.reason}
        return _artifact_check_cache

    from sklearn.model_selection import train_test_split

    df, _ = load_validated(Path(settings.dataset_path))
    X = df[list(FEATURES)]
    y = df[TARGET].astype(int)
    _, X_test, _, y_test = train_test_split(
        X,
        y,
        test_size=float(metadata.get("test_size", 0.2)),
        stratify=y,
        random_state=int(metadata.get("random_state", 42)),
    )

    sample = X_test.head(10)
    probabilities = predictor.predict_many(sample.to_dict("records"))
    rows = []
    for index, (_, row) in enumerate(sample.iterrows()):
        rows.append(
            {
                "latitude": round(float(row["latitude"]), 4),
                "longitude": round(float(row["longitude"]), 4),
                "rainfall_mm": round(float(row["rainfall_mm"]), 2),
                "actual_label": int(y_test.iloc[index]),
                "predicted_probability": probabilities[index] if index < len(probabilities) else None,
            }
        )

    _artifact_check_cache = {
        "available": True,
        "sampled_rows": rows,
        "note": (
            "Ten rows from the held-out synthetic test split, with the model's "
            "real output. Probabilities cluster near 0.5 because the features carry "
            "no signal - this demonstrates the artifact loads and runs; it does not "
            "demonstrate predictive skill."
        ),
    }
    return _artifact_check_cache


@router.get("/model", summary="Prototype model info and real evaluation results")
def model_info() -> dict:
    metrics_path = Path(settings.model_metrics)
    meta_path = Path(settings.model_metadata)

    if not metrics_path.exists() or not meta_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Model artifacts are not available. Run 'python -m app.ml.train' "
                "in the backend directory, then retry."
            ),
        )

    metrics = _load_json(metrics_path)
    metadata = _load_json(meta_path)

    try:
        _, integrity = load_validated(Path(settings.dataset_path))
    except Exception as exc:  # pragma: no cover - defensive
        integrity = {"error": str(exc)}

    return {
        "prototype": True,
        "reliable": False,
        "is_trained_model": True,
        "used_for_live_risk_estimates": False,
        "warning": metadata.get("warning"),
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("model_version"),
        "algorithm": metadata.get("algorithm"),
        "trained_at_utc": metadata.get("trained_at_utc"),
        "dataset_integrity": integrity,
        "metrics": metrics,
        "artifact_check": _artifact_check(),
        "limitations": metadata.get("limitations", []),
        "environment": metadata.get("environment", {}),
        "note": (
            "The live Chennai risk numbers in this dashboard come from the "
            "transparent rule-based engine (app/prediction/rule_based.py), not from "
            "this classifier."
        ),
    }
