"""Poisson soccer model for 1X2 probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, factorial

import numpy as np
import pandas as pd

from src.utils.probability import normalize_probabilities


@dataclass
class PoissonSoccerModel:
    """Estimate home/draw/away probabilities from expected goals."""

    max_goals: int = 8
    home_advantage_goals: float = 0.22
    league_home_goals: float = 1.35
    league_away_goals: float = 1.10
    attack: dict[str, float] | None = None
    defense: dict[str, float] | None = None

    def fit(self, results: pd.DataFrame) -> "PoissonSoccerModel":
        """Fit simple attack and defense multipliers from match results."""

        if results.empty:
            return self
        self.league_home_goals = float(results["goles_local"].mean())
        self.league_away_goals = float(results["goles_visitante"].mean())
        teams = sorted(set(results["local"]).union(results["visitante"]))
        attack: dict[str, float] = {}
        defense: dict[str, float] = {}
        league_avg = max((self.league_home_goals + self.league_away_goals) / 2, 0.1)
        for team in teams:
            scored = pd.concat(
                [
                    results.loc[results["local"] == team, "goles_local"],
                    results.loc[results["visitante"] == team, "goles_visitante"],
                ]
            )
            conceded = pd.concat(
                [
                    results.loc[results["local"] == team, "goles_visitante"],
                    results.loc[results["visitante"] == team, "goles_local"],
                ]
            )
            attack[team] = max(float(scored.mean()) / league_avg, 0.2) if not scored.empty else 1.0
            defense[team] = max(float(conceded.mean()) / league_avg, 0.2) if not conceded.empty else 1.0
        self.attack = attack
        self.defense = defense
        return self

    def expected_goals(self, home: str, away: str) -> tuple[float, float]:
        """Return expected goals for home and away."""

        attack = self.attack or {}
        defense = self.defense or {}
        home_xg = self.league_home_goals * attack.get(home, 1.0) * defense.get(away, 1.0)
        away_xg = self.league_away_goals * attack.get(away, 1.0) * defense.get(home, 1.0)
        return max(home_xg + self.home_advantage_goals, 0.05), max(away_xg, 0.05)

    def predict(self, home: str, away: str) -> dict[str, float]:
        """Return probabilities for L/E/V."""

        home_xg, away_xg = self.expected_goals(home, away)
        home_win = draw = away_win = 0.0
        for hg in range(self.max_goals + 1):
            for ag in range(self.max_goals + 1):
                prob = float(_poisson_pmf(hg, home_xg) * _poisson_pmf(ag, away_xg))
                if hg > ag:
                    home_win += prob
                elif hg == ag:
                    draw += prob
                else:
                    away_win += prob
        probs = normalize_probabilities([home_win, draw, away_win])
        return {"L": float(probs[0]), "E": float(probs[1]), "V": float(probs[2])}


def _poisson_pmf(k: int, lam: float) -> float:
    """Poisson PMF without requiring scipy."""

    return exp(-lam) * (lam**k) / factorial(k)
