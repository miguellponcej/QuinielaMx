"""Low-cost ticket strategies."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.config.games import GameConfig, OptimizationGoal, RiskProfile
from src.optimization.ticket_optimizer import OptimizedTicket, TicketOptimizer
from src.prediction.predictor import MatchPrediction


@dataclass
class LowCostStrategies:
    """Named optimization scenarios."""

    economico: OptimizedTicket
    balanceado: OptimizedTicket
    agresivo: OptimizedTicket
    personalizado: OptimizedTicket
    resumen: pd.DataFrame

    @property
    def economica(self) -> OptimizedTicket:
        """Backward-compatible alias."""

        return self.economico

    @property
    def balanceada(self) -> OptimizedTicket:
        """Backward-compatible alias."""

        return self.balanceado

    @property
    def agresiva(self) -> OptimizedTicket:
        """Backward-compatible alias."""

        return self.agresivo


def optimize_low_cost_ticket(
    predictions: list[MatchPrediction],
    game_config: GameConfig,
    budget: float,
) -> LowCostStrategies:
    """Generate economic, balanced, aggressive and personalized tickets."""

    optimizer = TicketOptimizer(game_config)
    economico = optimizer.optimize(
        predictions,
        budget=budget,
        risk_profile=RiskProfile.CONSERVATIVE,
        max_doubles=min(3, game_config.max_doubles or 3),
        max_triples=0,
        goal=OptimizationGoal.MIN_COST,
    )
    balanceado = optimizer.optimize(
        predictions,
        budget=budget,
        risk_profile=RiskProfile.BALANCED,
        max_doubles=min(5, game_config.max_doubles or 5),
        max_triples=min(1, game_config.max_triples or 1),
        goal=OptimizationGoal.MAX_EXPECTED_VALUE,
    )
    agresivo = optimizer.optimize(
        predictions,
        budget=budget,
        risk_profile=RiskProfile.AGGRESSIVE,
        max_doubles=min(6, game_config.max_doubles or 6),
        max_triples=min(2, game_config.max_triples or 2),
        goal=OptimizationGoal.MAX_UNCERTAINTY_COVERAGE,
    )
    personalizado = optimizer.optimize(
        predictions,
        budget=budget,
        risk_profile=RiskProfile.AGGRESSIVE,
        max_doubles=game_config.max_doubles,
        max_triples=game_config.max_triples,
        goal=OptimizationGoal.MAX_EXPECTED_VALUE,
    )
    rows = []
    for name, ticket in [
        ("Economico", economico),
        ("Balanceado", balanceado),
        ("Agresivo", agresivo),
        ("Personalizado", personalizado),
    ]:
        rows.append(
            {
                "estrategia": name,
                "combinaciones": ticket.combinations,
                "costo": ticket.cost,
                "prob_quiniela_completa": ticket.probability_all_correct,
                "dobles": sum(1 for selection in ticket.selections if len(selection) == 2),
                "triples": sum(1 for selection in ticket.selections if len(selection) == 3),
            }
        )
    return LowCostStrategies(
        economico=economico,
        balanceado=balanceado,
        agresivo=agresivo,
        personalizado=personalizado,
        resumen=pd.DataFrame(rows),
    )
