"""Train and evaluate the synthetic-data flood classifier prototype.

Run from the ``backend`` directory::

    python -m app.ml.train

Writes three artifacts into ``backend/models``:

* ``flood_model.joblib``   - fitted scikit-learn Pipeline (preprocessing + model)
* ``model_metadata.json``  - features, versions, dataset hash, imputation stats
* ``model_metrics.json``   - real train/test metrics, baselines, verdict

This model is a documented negative result. See ``app/ml/evaluate.py``.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..config import settings
from .dataset import (
    CATEGORICAL_FEATURES,
    FEATURES,
    NUMERIC_FEATURES,
    TARGET,
    load_validated,
)
from .evaluate import (
    build_verdict,
    classification_metrics,
    majority_baseline,
    shuffled_label_control,
    univariate_signal,
)

RANDOM_STATE = 42
TEST_SIZE = 0.2

MODEL_NAME = "flood-occurred-logreg"
MODEL_VERSION = "0.1.0"

PROTOTYPE_WARNING = (
    "PROTOTYPE TRAINED ON SYNTHETIC DATA. Verified to carry no measurable signal "
    "(test ROC-AUC indistinguishable from a shuffled-label control). These metrics "
    "describe a synthetic dataset, NOT real-world Chennai flood accuracy. This "
    "model is retained as a documented negative result and must not be used for "
    "operational flood prediction."
)


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), list(NUMERIC_FEATURES)),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_FEATURES),
            ),
        ],
        remainder="drop",
    )


def build_logistic_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("prep", build_preprocessor()),
            (
                "clf",
                LogisticRegression(max_iter=2000, random_state=RANDOM_STATE),
            ),
        ]
    )


def build_forest_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("prep", build_preprocessor()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _evaluate_pipeline(pipeline: Pipeline, X_train, X_test, y_train, y_test) -> dict:
    return {
        "train": classification_metrics(
            y_train, pipeline.predict(X_train), pipeline.predict_proba(X_train)[:, 1]
        ),
        "test": classification_metrics(
            y_test, pipeline.predict(X_test), pipeline.predict_proba(X_test)[:, 1]
        ),
    }


def _imputation_stats(X_train: pd.DataFrame) -> dict:
    numeric_mean = {
        col: round(float(X_train[col].mean()), 6) for col in NUMERIC_FEATURES
    }
    categorical_mode = {
        col: str(X_train[col].mode(dropna=True).iloc[0]) for col in CATEGORICAL_FEATURES
    }
    return {"numeric_mean": numeric_mean, "categorical_mode": categorical_mode}


def main() -> int:
    dataset_path = Path(settings.dataset_path)
    print(f"[1/6] Loading dataset: {dataset_path}")
    df, integrity = load_validated(dataset_path)
    print(
        f"      OK  {integrity['rows']} rows x {integrity['columns']} columns   "
        f"sha256={integrity['sha256'][:16]}..."
    )
    print(f"      target balance: {integrity['target_balance']}")

    X = df[list(FEATURES)]
    y = df[TARGET].astype(int)

    print(f"[2/6] Stratified {1 - TEST_SIZE:.0%}/{TEST_SIZE:.0%} split (seed={RANDOM_STATE})")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"      train={len(X_train)}  test={len(X_test)}")

    # The preprocessor is fitted inside the pipeline and only ever sees
    # X_train, so no test information reaches training (no leakage).
    print("[3/6] Fitting logistic regression baseline")
    logistic = build_logistic_pipeline()
    logistic.fit(X_train, y_train)
    logistic_metrics = _evaluate_pipeline(logistic, X_train, X_test, y_train, y_test)

    print("[4/6] Fitting random forest comparison")
    forest = build_forest_pipeline()
    forest.fit(X_train, y_train)
    forest_metrics = _evaluate_pipeline(forest, X_train, X_test, y_train, y_test)

    print("[5/6] Computing baselines and controls")
    baseline = majority_baseline(y_test)
    control = shuffled_label_control(
        build_logistic_pipeline, X_train, X_test, y_train, y_test
    )
    signal = univariate_signal(df, NUMERIC_FEATURES, CATEGORICAL_FEATURES)
    verdict = build_verdict(logistic_metrics, baseline, control)

    print("[6/6] Writing artifacts")
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(logistic, settings.model_artifact)

    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "artifact": settings.model_artifact.name,
        "task": "binary classification (flood_occurred)",
        "algorithm": "LogisticRegression",
        "prototype": True,
        "reliable": False,
        "warning": PROTOTYPE_WARNING,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "target_column": TARGET,
        "features": list(FEATURES),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "training_row_count": int(len(X_train)),
        "test_row_count": int(len(X_test)),
        "imputation": _imputation_stats(X_train),
        "dataset": {
            "path": integrity["path"],
            "rows": integrity["rows"],
            "columns": integrity["columns"],
            "sha256": integrity["sha256"],
            "provenance": integrity["provenance"],
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "limitations": [
            "Dataset is synthetic; the label is statistically independent of all features.",
            "Dataset is India-wide with only a handful of rows near Chennai.",
            "Elevation values in the dataset are implausible for city-scale analysis.",
            "The model cannot consume live Chennai zone inputs without imputing several columns.",
            "It is not an official flood-warning system and must not inform emergency decisions.",
        ],
    }

    metrics_payload = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "prototype": True,
        "generated_at_utc": metadata["trained_at_utc"],
        "warning": PROTOTYPE_WARNING,
        "primary_model": "logistic_regression",
        "logistic_regression": logistic_metrics,
        "random_forest_comparison": forest_metrics,
        "majority_class_baseline": baseline,
        "shuffled_label_control": control,
        "univariate_feature_signal": signal,
        "verdict": verdict,
        "dataset": metadata["dataset"],
        "environment": metadata["environment"],
    }

    settings.model_metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    settings.model_metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    print()
    print("=" * 74)
    print("RESULTS (real, not adjusted)")
    print("=" * 74)
    for label in ("train", "test"):
        m = logistic_metrics[label]
        print(
            f"  logistic [{label:5s}] acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
            f"rec={m['recall']:.4f} f1={m['f1']:.4f} auc={m['roc_auc']:.4f}"
        )
    print(
        f"  forest   [test ] acc={forest_metrics['test']['accuracy']:.4f} "
        f"auc={forest_metrics['test']['roc_auc']:.4f}"
    )
    print(f"  majority baseline accuracy ......... {baseline['accuracy']:.4f}")
    print(f"  shuffled-label control AUC ......... {control['roc_auc_vs_true_labels']:.4f}")
    print(
        f"  improvement over baseline .......... "
        f"{verdict['accuracy_improvement_over_baseline']:+.4f}"
    )
    print(f"  confusion (test) TP/FP/FN/TN ....... ", end="")
    cm = logistic_metrics["test"]["confusion_matrix"]
    print(f"{cm['true_positive']}/{cm['false_positive']}/{cm['false_negative']}/{cm['true_negative']}")
    print(f"\n  VERDICT signal_detected={verdict['signal_detected']}")
    print(f"  {verdict['summary']}")
    print(f"\n  artifacts written to {settings.models_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
