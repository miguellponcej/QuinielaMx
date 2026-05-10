"""Monte Carlo simulation for quiniela strategies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config.games import GameConfig
from src.prediction.predictor import MatchPrediction


@dataclass
class SimulationResult:
    """Simulation summary."""

    summary: pd.DataFrame
    hits_distribution: pd.DataFrame
    raw_hits: np.ndarray


class MonteCarloSimulator:
    """Simulate quiniela outcomes from estimated probabilities."""

    def __init__(self, game_config: GameConfig, seed: int = 42) -> None:
        self.game_config = game_config
        self.rng = np.random.default_rng(seed)

    def simulate(
        self,
        predictions: list[MatchPrediction],
        selections: list[list[str]],
        scenarios: int = 100_000,
        prize_by_hits: dict[int, float] | None = None,
    ) -> SimulationResult:
        """Run Monte Carlo scenarios and summarize hits."""

        if scenarios <= 0:
            raise ValueError("El numero de escenarios debe ser mayor que cero.")
        if len(predictions) != len(selections):
            raise ValueError("Las selecciones deben corresponder a cada partido predicho.")
        self.game_config.validate_ticket(selections)
        option_order = list(self.game_config.options)
        probability_matrix = np.array(
            [[prediction.probabilities[option] for option in option_order] for prediction in predictions],
            dtype=float,
        )
        draws = np.empty((scenarios, len(predictions)), dtype=int)
        for idx, probs in enumerate(probability_matrix):
            draws[:, idx] = self.rng.choice(len(option_order), size=scenarios, p=probs)
        selected_sets = [set(option_order.index(item) for item in selection) for selection in selections]
        hits = np.zeros(scenarios, dtype=int)
        for idx, selected in enumerate(selected_sets):
            hits += np.isin(draws[:, idx], list(selected))
        max_hits = len(predictions)
        combinations = self.game_config.count_combinations(selections)
        cost = self.game_config.calculate_cost(selections)
        prize_by_hits = prize_by_hits or {}
        payout = np.array([prize_by_hits.get(int(hit), 0.0) for hit in hits])
        summary_rows = [
            {"metrica": f"Probabilidad de {target} aciertos", "valor": float(np.mean(hits >= target))}
            for target in range(max_hits, max(max_hits - 4, 0), -1)
        ]
        summary_rows.extend(
            [
                {"metrica": "Probabilidad de recuperar costo", "valor": float(np.mean(payout >= cost))},
                {"metrica": "Costo", "valor": cost},
                {"metrica": "Combinaciones", "valor": combinations},
                {"metrica": "Valor esperado estimado", "valor": float(np.mean(payout) - cost)},
            ]
        )
        unique, counts = np.unique(hits, return_counts=True)
        distribution = pd.DataFrame(
            {"aciertos": unique, "escenarios": counts, "probabilidad": counts / scenarios}
        )
        return SimulationResult(
            summary=pd.DataFrame(summary_rows),
            hits_distribution=distribution,
            raw_hits=hits,
        )
