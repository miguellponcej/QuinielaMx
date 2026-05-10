"""Lightweight Dixon-Coles style adjustment."""

from __future__ import annotations

from src.utils.probability import normalize_probabilities


def adjust_low_scoring_draws(probabilities: dict[str, float], rho: float = 0.06) -> dict[str, float]:
    """Boost draw probability slightly to mimic low-score correlation correction."""

    adjusted = {
        "L": probabilities.get("L", 0.0) * (1 - rho / 2),
        "E": probabilities.get("E", 0.0) * (1 + rho),
        "V": probabilities.get("V", 0.0) * (1 - rho / 2),
    }
    values = normalize_probabilities([adjusted["L"], adjusted["E"], adjusted["V"]])
    return {"L": float(values[0]), "E": float(values[1]), "V": float(values[2])}

