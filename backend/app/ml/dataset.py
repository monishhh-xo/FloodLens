"""Dataset loading and integrity validation for the flood-risk CSV.

The shipped dataset (``data/flood_risk_dataset_india.csv``) is India-wide and,
as :mod:`app.ml.evaluate` demonstrates, synthetic: the label is statistically
independent of every feature. The loader therefore does two jobs:

1. Normalise the non-ASCII headers (``Temperature (°C)``, ``River Discharge
   (m³/s)``) into stable ASCII names so the fitted pipeline is portable.
2. Assert the expected shape hard, so a swapped-in *real* dataset cannot be
   silently mis-read - it will fail loudly and need an explicit update here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

TARGET = "flood_occurred"

# Original non-ASCII headers, in file order.
EXPECTED_RAW_COLUMNS: tuple[str, ...] = (
    "Latitude",
    "Longitude",
    "Rainfall (mm)",
    "Temperature (\u00b0C)",
    "Humidity (%)",
    "River Discharge (m\u00b3/s)",
    "Water Level (m)",
    "Elevation (m)",
    "Land Cover",
    "Soil Type",
    "Population Density",
    "Infrastructure",
    "Historical Floods",
    "Flood Occurred",
)

RENAME: dict[str, str] = {
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Rainfall (mm)": "rainfall_mm",
    "Temperature (\u00b0C)": "temperature_c",
    "Humidity (%)": "humidity_pct",
    "River Discharge (m\u00b3/s)": "river_discharge_m3s",
    "Water Level (m)": "water_level_m",
    "Elevation (m)": "elevation_m",
    "Land Cover": "land_cover",
    "Soil Type": "soil_type",
    "Population Density": "population_density",
    "Infrastructure": "infrastructure",
    "Historical Floods": "historical_floods",
    "Flood Occurred": "flood_occurred",
}

NUMERIC_FEATURES: tuple[str, ...] = (
    "latitude",
    "longitude",
    "rainfall_mm",
    "temperature_c",
    "humidity_pct",
    "river_discharge_m3s",
    "water_level_m",
    "elevation_m",
    "population_density",
    "infrastructure",
    "historical_floods",
)

CATEGORICAL_FEATURES: tuple[str, ...] = ("land_cover", "soil_type")

FEATURES: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

EXPECTED_ROWS = 10_000

DATASET_PROVENANCE = (
    "Flood risk dataset for India, supplied as a single CSV of 10,000 synthetic "
    "samples. It is NOT an observational record of real flood events."
)


class DatasetValidationError(RuntimeError):
    """Raised when the dataset does not match the documented schema."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw(path: Path) -> pd.DataFrame:
    """Read the CSV with the correct encoding and ASCII column names.

    Encoding is UTF-8 *without* BOM, and two headers contain non-ASCII
    characters, so ``encoding="utf-8"`` is required (``utf-8-sig`` also works).
    """
    if not path.exists():
        raise DatasetValidationError(
            f"Dataset not found at {path}. Expected "
            f"'data/flood_risk_dataset_india.csv' in the project root."
        )
    df = pd.read_csv(path, encoding="utf-8")
    df.columns = [str(c).strip() for c in df.columns]
    return df.rename(columns=RENAME)


def validate(df: pd.DataFrame, *, expected_rows: int = EXPECTED_ROWS) -> dict:
    """Assert the documented schema and return an integrity report."""
    problems: list[str] = []

    missing_cols = [c for c in RENAME.values() if c not in df.columns]
    if missing_cols:
        problems.append(f"missing expected columns: {missing_cols}")

    if len(df.columns) != len(EXPECTED_RAW_COLUMNS):
        problems.append(
            f"expected {len(EXPECTED_RAW_COLUMNS)} columns, found {len(df.columns)}"
        )

    if len(df) != expected_rows:
        problems.append(f"expected {expected_rows} rows, found {len(df)}")

    if not problems:
        null_cols = {c: int(n) for c, n in df.isna().sum().items() if int(n) > 0}
        if null_cols:
            problems.append(f"null values present: {null_cols}")

        dupe_rows = int(df.duplicated().sum())
        if dupe_rows:
            problems.append(f"{dupe_rows} duplicate rows")

        target_vals = set(pd.unique(df[TARGET]))
        if not target_vals.issubset({0, 1}):
            problems.append(f"target must be binary 0/1, found {sorted(target_vals)}")

    if problems:
        raise DatasetValidationError("; ".join(problems))

    target_counts = df[TARGET].value_counts().sort_index().to_dict()
    total = len(df)
    return {
        "rows": int(total),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "sha256": None,  # filled by integrity_report()
        "target_column": TARGET,
        "target_counts": {str(int(k)): int(v) for k, v in target_counts.items()},
        "target_balance": {
            str(int(k)): round(v / total, 4) for k, v in target_counts.items()
        },
        "null_values": 0,
        "duplicate_rows": 0,
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "provenance": DATASET_PROVENANCE,
    }


def integrity_report(path: Path) -> dict:
    """Load, validate and hash the dataset in one call."""
    df = load_raw(path)
    report = validate(df)
    report["sha256"] = sha256_of(path)
    report["path"] = str(path)
    return report


def load_validated(path: Path) -> tuple[pd.DataFrame, dict]:
    df = load_raw(path)
    report = validate(df)
    report["sha256"] = sha256_of(path)
    report["path"] = str(path)
    return df, report
