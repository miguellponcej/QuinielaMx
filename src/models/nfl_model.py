"""American football margin model."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

from src.utils.probability import normalize_probabilities


@dataclass
class NFLMarginModel:
    """Estimate Protouch probabilities from expected scoring margin."""

    sigma_points: float = 13.5
    home_field_points: float = 1.7

    def predict_from_spread(self, spread_home: float | None = None) -> dict[str, float]:
        """Return L/D/V where D is absolute margin <= 6.

        spread_home is interpreted as expected home margin. Positive means home favored.
        """

        mean_margin = self.home_field_points if spread_home is None else spread_home
        p_visit_big = _normal_cdf(-6.0, mean_margin, self.sigma_points)
        p_local_big = 1 - _normal_cdf(6.0, mean_margin, self.sigma_points)
        p_close = max(0.0, 1 - p_local_big - p_visit_big)
        probs = normalize_probabilities([p_local_big, p_close, p_visit_big])
        return {"L": float(probs[0]), "D": float(probs[1]), "V": float(probs[2])}


def _normal_cdf(x: float, mean: float, sigma: float) -> float:
    """Normal CDF without requiring scipy."""

    z = (x - mean) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))
