"""Weighted probability ensembles."""

from __future__ import annotations

from collections.abc import Mapping

from src.utils.probability import normalize_probabilities


def weighted_ensemble(
    predictions: list[Mapping[str, float]],
    weights: list[float] | None = None,
) -> dict[str, float]:
    """Combine probability dictionaries with weights."""

    if not predictions:
        raise ValueError("At least one prediction is required.")
    keys = list(predictions[0].keys())
    weights = weights or [1.0] * len(predictions)
    if len(weights) != len(predictions):
        raise ValueError("Weights length must match predictions length.")
    totals = {key: 0.0 for key in keys}
    for pred, weight in zip(predictions, weights, strict=True):
        for key in keys:
            totals[key] += float(pred.get(key, 0.0)) * weight
    probs = normalize_probabilities([totals[key] for key in keys])
    return dict(zip(keys, map(float, probs), strict=True))

