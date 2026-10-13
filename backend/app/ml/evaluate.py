"""Evaluation helpers proving the shipped dataset carries no usable signal.

The point of this module is honesty. It does not try to make the numbers look
good; it reports the model's real performance *and* the two controls that make
that performance interpretable:

* majority-class baseline - what you get by always predicting the common class;
* shuffled-label control - the same pipeline fitted on randomly permuted
  labels. If the real target scores the same as the shuffled one, the features
  contain no information about the label.

Callers must not present these numbers as real-world Chennail accuracy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# A model is only considered to have found signal if it clearly beats chance
# AND clearly beats its own shuffled-label control.
MIN_AUC_ABOVE_CHANCE = 0.55
MIN_MARGIN_OVER_CONTROL = 0.03


def classification_metrics(y_true, y_pred, y_proba) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    y_proba = np.asarray(y_proba)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    return {
        "n": int(len(y_true)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_proba)), 4),
        "confusion_matrix": {
            "labels": ["0 = no flood", "1 = flood occurred"],
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "true_positive": tp,
        },
    }


def majority_baseline(y_test) -> dict:
    y_test = np.asarray(y_test)
    counts = np.bincount(y_test, minlength=2)
    majority = int(np.argmax(counts))
    pred = np.full_like(y_test, majority)
    return {
        "strategy": f"always predict {majority}",
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "positive_rate_in_test": round(float(counts[1] / counts.sum()), 4),
    }


def univariate_signal(df: pd.DataFrame, numeric_features, categorical_features) -> dict:
    """Per-feature signal scan. AUC 0.5 means the feature is uninformative."""
    y = df["flood_occurred"].to_numpy()
    numeric: list[dict] = []
    for col in numeric_features:
        if col == "flood_occurred":
            continue
        auc = float(roc_auc_score(y, df[col].to_numpy()))
        numeric.append(
            {
                "feature": col,
                "kind": "numeric",
                "auc": round(auc, 4),
                "distance_from_chance": round(abs(auc - 0.5), 4),
            }
        )

    categorical: list[dict] = []
    for col in categorical_features:
        rates = (
            df.groupby(col, observed=True)["flood_occurred"]
            .agg(["mean", "size"])
            .reset_index()
        )
        spread = float(rates["mean"].max() - rates["mean"].min())
        categorical.append(
            {
                "feature": col,
                "kind": "categorical",
                "levels": [
                    {
                        "level": str(r[col]),
                        "n": int(r["size"]),
                        "flood_rate": round(float(r["mean"]), 4),
                    }
                    for _, r in rates.iterrows()
                ],
                "flood_rate_spread": round(spread, 4),
            }
        )

    numeric.sort(key=lambda d: -d["distance_from_chance"])
    return {"numeric": numeric, "categorical": categorical}


def shuffled_label_control(pipeline_factory, X_train, X_test, y_train, y_test, seed: int = 7) -> dict:
    """Fit the identical pipeline on permuted labels."""
    rng = np.random.default_rng(seed)
    y_shuffled = rng.permutation(np.asarray(y_train))

    pipeline = pipeline_factory()
    pipeline.fit(X_train, y_shuffled)
    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    # AUC against the *real* test labels measures the same statistic as the
    # primary model, so the two are directly comparable.
    return {
        "seed": seed,
        "roc_auc_vs_true_labels": round(float(roc_auc_score(y_test, proba)), 4),
        "accuracy_vs_true_labels": round(float(accuracy_score(y_test, pred)), 4),
        "note": (
            "Same pipeline and split, labels randomly permuted during training. "
            "Scores close to the primary model indicate the features carry no "
            "predictive information."
        ),
    }


def build_verdict(metrics: dict, baseline: dict, control: dict) -> dict:
    test_auc = float(metrics["test"]["roc_auc"])
    control_auc = float(control["roc_auc_vs_true_labels"])
    improvement = round(test_auc - float(baseline["accuracy"]), 4)
    auc_above_chance = round(test_auc - 0.5, 4)
    margin_over_control = round(test_auc - control_auc, 4)

    signal_detected = (
        test_auc >= MIN_AUC_ABOVE_CHANCE and margin_over_control >= MIN_MARGIN_OVER_CONTROL
    )

    if signal_detected:
        summary = (
            "The model beats chance and its shuffled-label control. Further work "
            "is still required before any operational use."
        )
    else:
        summary = (
            "No usable signal. Test ROC-AUC is indistinguishable from a "
            "shuffled-label control and adds essentially nothing over the "
            "majority-class baseline, so this artifact must not be used to "
            "predict real floods."
        )

    return {
        "signal_detected": bool(signal_detected),
        "test_auc": test_auc,
        "auc_above_chance": auc_above_chance,
        "control_auc": control_auc,
        "margin_over_control": margin_over_control,
        "accuracy_improvement_over_baseline": improvement,
        "thresholds": {
            "min_auc": MIN_AUC_ABOVE_CHANCE,
            "min_margin_over_control": MIN_MARGIN_OVER_CONTROL,
        },
        "summary": summary,
    }
