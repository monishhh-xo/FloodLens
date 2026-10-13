"""Dataset integrity and the negative-result evidence.

These tests are the executable form of the honesty claims in the README: if a
future dataset swap introduced real signal, or if someone quietly removed the
"no signal" conclusion, these tests fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import settings
from app.ml.dataset import (
    EXPECTED_RAW_COLUMNS,
    FEATURES,
    NUMERIC_FEATURES,
    RENAME,
    TARGET,
    load_validated,
)

pytestmark = pytest.mark.skipif(
    not Path(settings.dataset_path).exists(),
    reason="Dataset not available.",
)


@pytest.fixture(scope="module")
def dataset():
    return load_validated(Path(settings.dataset_path))


def test_dataset_has_ten_thousand_rows_and_fourteen_columns(dataset):
    df, report = dataset
    assert report["rows"] == 10000
    assert report["columns"] == 14
    assert len(EXPECTED_RAW_COLUMNS) == 14
    # The loader renames the non-ASCII headers to stable ASCII names.
    assert list(df.columns) == list(RENAME.values())
    assert set(RENAME) == set(EXPECTED_RAW_COLUMNS)


def test_tagged_column_names_are_read_correctly(dataset):
    """The file contains degree and superscript-three characters in two headers."""
    df, _ = dataset
    assert "temperature_c" in df.columns
    assert "river_discharge_m3s" in df.columns


def test_dataset_has_no_nulls_duplicates_and_is_binary(dataset):
    df, report = dataset
    assert report["null_values"] == 0
    assert report["duplicate_rows"] == 0
    assert df.isna().sum().sum() == 0
    assert set(df[TARGET].unique()) == {0, 1}


def test_target_is_roughly_balanced(dataset):
    _, report = dataset
    balance = report["target_balance"]
    assert 0.45 < balance["0"] < 0.55
    assert 0.45 < balance["1"] < 0.55


def test_every_feature_is_uninformative(dataset):
    """AUC ~0.5 for every feature is the evidence that the data is synthetic."""
    from sklearn.metrics import roc_auc_score

    df, _ = dataset
    y = df[TARGET].to_numpy()
    for column in NUMERIC_FEATURES:
        auc = float(roc_auc_score(y, df[column].to_numpy()))
        assert 0.45 < auc < 0.55, f"{column} unexpectedly carries signal (AUC={auc:.3f})"


def test_categorical_flood_rates_are_near_a_coin_flip(dataset):
    df, _ = dataset
    for column in ("land_cover", "soil_type"):
        rates = df.groupby(column, observed=True)[TARGET].mean()
        assert float(rates.max() - rates.min()) < 0.10


def test_numeric_columns_are_uniformly_distributed(dataset):
    """Synthetic generators produce near-perfect uniform deciles."""
    df, _ = dataset
    for column in ("rainfall_mm", "elevation_m", "population_density"):
        values = df[column].sort_values().to_numpy()
        deciles = [len(values[i * 1000 : (i + 1) * 1000]) for i in range(10)]
        assert deciles == [1000] * 10, f"{column} is not uniformly distributed"


def test_elevation_values_are_implausible_for_city_scale_analysis(dataset):
    """Documented limitation: the dataset reports alpine heights for coastal cities."""
    df, _ = dataset
    chennai = df[(df["latitude"].between(12.5, 13.3)) & (df["longitude"].between(79.9, 80.4))]
    assert len(chennai) < 50, "expected only a handful of rows near Chennai"
    if len(chennai):
        assert chennai["elevation_m"].max() > 1000


# --- pipeline behaviour ----------------------------------------------------
def _artifacts_available() -> bool:
    return settings.model_artifact.exists() and settings.model_metrics.exists()


needs_artifacts = pytest.mark.skipif(
    not _artifacts_available(), reason="Run 'python -m app.ml.train' first."
)


@needs_artifacts
def test_preprocessor_was_fitted_on_the_training_split_only(dataset):
    """Leakage check: scaler statistics must equal train-split statistics."""
    import joblib
    from sklearn.model_selection import train_test_split

    df, _ = dataset
    pipeline = joblib.load(settings.model_artifact)

    X = df[list(FEATURES)]
    y = df[TARGET].astype(int)
    X_train, _, _, _ = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    scaler = pipeline.named_steps["prep"].named_transformers_["num"]
    index = list(NUMERIC_FEATURES).index("rainfall_mm")

    train_mean = float(X_train["rainfall_mm"].mean())
    full_mean = float(X["rainfall_mm"].mean())

    assert abs(scaler.mean_[index] - train_mean) < 1e-6
    assert abs(scaler.mean_[index] - full_mean) > 1e-4


@needs_artifacts
def test_pipeline_predictions_are_deterministic(dataset):
    import joblib

    df, _ = dataset
    pipeline = joblib.load(settings.model_artifact)
    sample = df[list(FEATURES)].head(25)

    first = pipeline.predict_proba(sample)[:, 1]
    second = pipeline.predict_proba(sample)[:, 1]
    assert all(abs(a - b) < 1e-12 for a, b in zip(first, second))


@needs_artifacts
def test_predictions_hover_around_chance(dataset):
    """A signal-free model must not produce confident probabilities."""
    import joblib

    df, _ = dataset
    pipeline = joblib.load(settings.model_artifact)
    probabilities = pipeline.predict_proba(df[list(FEATURES)].head(2000))[:, 1]
    assert probabilities.min() > 0.2
    assert probabilities.max() < 0.8


@needs_artifacts
def test_recorded_metrics_are_reproducible():
    """Re-running training with the same seed must give the same test AUC."""
    import json

    metrics = json.loads(Path(settings.model_metrics).read_text(encoding="utf-8"))
    recorded = metrics["logistic_regression"]["test"]["roc_auc"]

    from app.ml.train import RANDOM_STATE, TEST_SIZE, build_logistic_pipeline
    from sklearn.model_selection import train_test_split

    df, _ = load_validated(Path(settings.dataset_path))
    X = df[list(FEATURES)]
    y = df[TARGET].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    pipeline = build_logistic_pipeline().fit(X_train, y_train)

    from sklearn.metrics import roc_auc_score

    recomputed = round(float(roc_auc_score(y_test, pipeline.predict_proba(X_test)[:, 1])), 4)
    assert abs(recomputed - recorded) < 1e-9, (
        f"recorded AUC {recorded} != recomputed {recomputed}; "
        "the recorded metrics must come from the real training run."
    )


@needs_artifacts
def test_metadata_documents_limitations():
    import json

    metadata = json.loads(Path(settings.model_metadata).read_text(encoding="utf-8"))
    assert metadata["prototype"] is True
    assert metadata["reliable"] is False
    assert "SYNTHETIC" in metadata["warning"].upper()
    assert len(metadata["limitations"]) >= 4
    assert metadata["dataset"]["sha256"]


def test_rule_engine_ignores_the_ml_artifact():
    """The live risk path is the rule engine, independent of the dataset."""
    from app.prediction.rule_based import AssessInputs
    from app.prediction.registry import get_rule_predictor

    predictor = get_rule_predictor()
    inputs = AssessInputs(
        rainfall_mm_1h=60.0,
        rainfall_mm_24h=200.0,
        forecast_mm_next_24h=150.0,
        drainage_capacity_index=0.3,
        elevation_class="Low",
        imperviousness_pct=85.0,
        water_proximity_m=100.0,
    )
    result = predictor.assess(inputs)
    assert result.engine_mode == "rule-based-demo"
    # 30 + 25 + 15 rainfall, + 7 drainage deficit, + 10 low elevation,
    # + 5.1 imperviousness, + 3.6 water proximity = 95.7
    assert result.score == 95.7
    assert result.risk_level == "Severe"


def test_rule_engine_is_deterministic_and_monotonic():
    from app.prediction.rule_based import AssessInputs
    from app.prediction.registry import get_rule_predictor

    predictor = get_rule_predictor()
    base = dict(
        rainfall_mm_1h=10.0,
        rainfall_mm_24h=40.0,
        forecast_mm_next_24h=20.0,
        drainage_capacity_index=0.5,
        elevation_class="Mid",
        imperviousness_pct=50.0,
        water_proximity_m=500.0,
    )
    first = predictor.assess(AssessInputs(**base))
    second = predictor.assess(AssessInputs(**base))
    assert first == second

    wetter = predictor.assess(AssessInputs(**{**base, "rainfall_mm_1h": 55.0}))
    assert wetter.score > first.score

    better_drainage = predictor.assess(AssessInputs(**{**base, "drainage_capacity_index": 1.0}))
    assert better_drainage.score <= first.score


def test_rule_engine_clamps_extreme_inputs():
    from app.prediction.rule_based import AssessInputs
    from app.prediction.registry import get_rule_predictor

    predictor = get_rule_predictor()
    result = predictor.assess(
        AssessInputs(
            rainfall_mm_1h=9999.0,
            rainfall_mm_24h=9999.0,
            forecast_mm_next_24h=9999.0,
            drainage_capacity_index=-5.0,
            elevation_class="Low",
            imperviousness_pct=500.0,
            water_proximity_m=-100.0,
        )
    )
    assert 0.0 <= result.score <= 100.0
