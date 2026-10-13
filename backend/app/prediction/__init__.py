"""Prediction engines for FloodLens AI.

Two engines live here, deliberately separated:

* ``rule_based`` - the transparent, deterministic scoring prototype that
  actually produces every risk number shown for a Chennai zone.
* ``ml_predictor`` - wraps the scikit-learn artifact trained on
  ``data/flood_risk_dataset_india.csv``. That dataset is synthetic and,
  as verified in ``app/ml/evaluate.py``, carries no measurable signal, so the
  artifact is exposed as a documented negative result and is always flagged
  ``reliable=False``.

``base`` holds the shared contracts so a *real* trained model can be dropped in
later by implementing the same ``Predictor`` protocol.
"""

from .base import Predictor, RiskFactor, RiskResult
from .registry import get_ml_predictor, get_rule_predictor

__all__ = [
    "Predictor",
    "RiskFactor",
    "RiskResult",
    "get_rule_predictor",
    "get_ml_predictor",
]
