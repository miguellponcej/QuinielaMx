"""Odds conversion utilities."""

from __future__ import annotations

from collections.abc import Mapping

from src.utils.probability import normalize_probabilities


def american_to_decimal(american: float) -> float:
    """Convert American odds to decimal odds."""

    if american > 0:
        return 1 + american / 100
    if american < 0:
        return 1 + 100 / abs(american)
    raise ValueError("American odds cannot be zero.")


def decimal_to_implied_probability(decimal: float) -> float:
    """Convert decimal odds to implied probability."""

    if decimal <= 1:
        raise ValueError("Decimal odds must be greater than 1.")
    return 1 / decimal


def remove_vig(decimal_odds: Mapping[str, float]) -> dict[str, float]:
    """Return no-vig probabilities from decimal odds."""

    implied = {key: decimal_to_implied_probability(value) for key, value in decimal_odds.items()}
    normalized = normalize_probabilities(list(implied.values()))
    return dict(zip(implied.keys(), normalized, strict=True))

