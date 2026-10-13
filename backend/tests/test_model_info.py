from __future__ import annotations

import pytest


def _artifacts_exist() -> bool:
    from app.config import settings

    return settings.model_artifact.exists() and settings.model_metrics.exists()


needs_artifacts = pytest.mark.skipif(
    not _artifacts_exist(),
    reason="Run 'python -m app.ml.train' to generate model artifacts.",
)


@needs_artifacts
def test_model_info_reports_real_metrics(client):
    response = client.get("/api/model")
    assert response.status_code == 200
    body = response.json()

    assert body["prototype"] is True
    assert body["reliable"] is False
    assert body["is_trained_model"] is True
    assert body["used_for_live_risk_estimates"] is False
    assert "SYNTHETIC" in body["warning"].upper()

    metrics = body["metrics"]
    assert 0.0 <= metrics["logistic_regression"]["test"]["accuracy"] <= 1.0
    assert 0.0 <= metrics["logistic_regression"]["test"]["roc_auc"] <= 1.0
    cm = metrics["logistic_regression"]["test"]["confusion_matrix"]
    assert cm["true_positive"] + cm["true_negative"] > 0
    assert metrics["majority_class_baseline"]["accuracy"] > 0
    assert metrics["shuffled_label_control"]["roc_auc_vs_true_labels"] is not None


@needs_artifacts
def test_model_info_verifies_dataset_integrity_at_runtime(client):
    body = client.get("/api/model").json()
    integrity = body["dataset_integrity"]

    assert integrity["rows"] == 10000
    assert integrity["columns"] == 14
    assert integrity["null_values"] == 0
    assert integrity["duplicate_rows"] == 0
    assert set(integrity["target_counts"]) == {"0", "1"}


@needs_artifacts
def test_verdict_states_there_is_no_signal(client):
    body = client.get("/api/model").json()
    verdict = body["metrics"]["verdict"]

    assert verdict["signal_detected"] is False
    assert verdict["auc_above_chance"] < 0.05
    assert "no usable signal" in verdict["summary"].lower()


@needs_artifacts
def test_metrics_are_not_dressed_up_as_success(client):
    """Guard against someone later hard-coding flattering numbers."""
    body = client.get("/api/model").json()
    test_metrics = body["metrics"]["logistic_regression"]["test"]
    baseline = body["metrics"]["majority_class_baseline"]["accuracy"]

    # The honest expectation for a signal-free dataset.
    assert test_metrics["roc_auc"] < 0.60
    assert abs(test_metrics["accuracy"] - baseline) < 0.05


@needs_artifacts
def test_artifact_loads_and_runs_on_held_out_rows(client):
    body = client.get("/api/model").json()
    check = body["artifact_check"]

    assert check["available"] is True
    assert len(check["sampled_rows"]) == 10
    for row in check["sampled_rows"]:
        assert 0.0 <= row["predicted_probability"] <= 1.0
        assert row["actual_label"] in (0, 1)
