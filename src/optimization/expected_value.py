"""Expected value helpers."""

from __future__ import annotations


def expected_value(probabilities: dict[int, float], prizes: dict[int, float], cost: float) -> float:
    """Compute expected value from hit probabilities and prizes."""

    return sum(probabilities.get(hits, 0.0) * prizes.get(hits, 0.0) for hits in prizes) - cost


def roi(expected_profit: float, cost: float) -> float:
    """Return ROI from expected profit and cost."""

    if cost <= 0:
        raise ValueError("Cost must be positive.")
    return expected_profit / cost

