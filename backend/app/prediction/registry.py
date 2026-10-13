"""Engine registry.

Keeps a single cached instance of each predictor so HTTP handlers do not reload
the joblib artifact per request. If a real, signal-bearing model is ever
trained, ``get_rule_predictor`` can be pointed at it without touching the API
layer - the router depends on the ``Predictor`` protocol, not on the class.
"""

from __future__ import annotations

from .ml_predictor import MlPrototypePredictor
from .rule_based import RuleBasedPredictor

_rule_predictor: RuleBasedPredictor | None = None
_ml_predictor: MlPrototypePredictor | None = None


def get_rule_predictor() -> RuleBasedPredictor:
    global _rule_predictor
    if _rule_predictor is None:
        _rule_predictor = RuleBasedPredictor()
    return _rule_predictor


def get_ml_predictor() -> MlPrototypePredictor:
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MlPrototypePredictor.load()
    return _ml_predictor


def reset_ml_predictor() -> None:
    """Test helper: force a reload on next access."""
    global _ml_predictor
    _ml_predictor = None
