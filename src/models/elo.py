"""Simple Elo model."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class EloModel:
    """Team Elo ratings with home advantage."""

    base_rating: float = 1500.0
    k_factor: float = 24.0
    home_advantage: float = 65.0
    ratings: dict[str, float] = field(default_factory=dict)

    def rating(self, team: str) -> float:
        """Return rating for a team."""

        return self.ratings.get(team, self.base_rating)

    @staticmethod
    def expected(rating_a: float, rating_b: float) -> float:
        """Return expected score for A."""

        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def predict_home_win(self, home: str, away: str) -> float:
        """Return home win probability for a two-outcome matchup."""

        return self.expected(self.rating(home) + self.home_advantage, self.rating(away))

    def update_match(self, home: str, away: str, home_score: float, away_score: float) -> None:
        """Update ratings from one match."""

        home_rating = self.rating(home)
        away_rating = self.rating(away)
        expected_home = self.expected(home_rating + self.home_advantage, away_rating)
        actual_home = 1.0 if home_score > away_score else 0.5 if home_score == away_score else 0.0
        change = self.k_factor * (actual_home - expected_home)
        self.ratings[home] = home_rating + change
        self.ratings[away] = away_rating - change

    def fit(self, results: pd.DataFrame) -> "EloModel":
        """Fit ratings from rows with local, visitante, goles/puntos columns."""

        for row in results.sort_values("fecha").itertuples(index=False):
            home_score = getattr(row, "goles_local", getattr(row, "puntos_local", None))
            away_score = getattr(row, "goles_visitante", getattr(row, "puntos_visitante", None))
            if home_score is None or away_score is None:
                continue
            self.update_match(str(row.local), str(row.visitante), float(home_score), float(away_score))
        return self

