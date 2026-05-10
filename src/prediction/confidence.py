"""Confidence labels."""

from __future__ import annotations

from collections.abc import Sequence

from src.utils.probability import confidence_from_probs


def confidence_label(probabilities: Sequence[float]) -> str:
    """Return Alta, Media or Baja confidence."""

    score = confidence_from_probs(probabilities)
    if score >= 0.60:
        return "Alta"
    if score >= 0.48:
        return "Media"
    return "Baja"


def risk_score(probabilities: Sequence[float]) -> float:
    """Return risk score in [0, 1]. Higher means more uncertain."""

    return 1 - confidence_from_probs(probabilities)

