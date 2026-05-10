"""Probability utilities."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def normalize_probabilities(values: Sequence[float], epsilon: float = 1e-12) -> np.ndarray:
    """Normalize non-negative values into probabilities."""

    arr = np.asarray(values, dtype=float)
    arr = np.clip(arr, epsilon, None)
    total = arr.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Cannot normalize invalid probabilities.")
    return arr / total


def entropy(probabilities: Sequence[float]) -> float:
    """Return normalized entropy in [0, 1]."""

    probs = normalize_probabilities(probabilities)
    raw = -float(np.sum(probs * np.log(probs)))
    return raw / math.log(len(probs))


def confidence_from_probs(probabilities: Sequence[float]) -> float:
    """Return confidence score in [0, 1] from max probability and entropy."""

    probs = normalize_probabilities(probabilities)
    return float(0.65 * probs.max() + 0.35 * (1 - entropy(probs)))


def top_indices(probabilities: Sequence[float], n: int) -> list[int]:
    """Return indexes of top n probabilities."""

    arr = np.asarray(probabilities, dtype=float)
    return list(np.argsort(arr)[::-1][:n])


def cumulative_ticket_probability(probability_rows: Sequence[Sequence[float]], selections: Sequence[Sequence[int]]) -> float:
    """Return probability that all selected match outcomes are correct."""

    total = 1.0
    for probs, selected in zip(probability_rows, selections):
        row = normalize_probabilities(probs)
        total *= float(row[list(selected)].sum())
    return total

