"""Ticket optimization under budget and coverage constraints."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from src.config.games import GameConfig, OptimizationGoal, RiskProfile
from src.prediction.predictor import MatchPrediction
from src.utils.probability import cumulative_ticket_probability, entropy, top_indices


HIGH_UNCERTAINTY_ENTROPY = 0.92
CLOSE_GAME_GAP = 0.12
EXTREME_UNCERTAINTY_GAP = 0.06


@dataclass
class OptimizedTicket:
    """Optimized ticket output."""

    selections: list[list[str]]
    combinations: int
    cost: float
    probability_all_correct: float
    table: pd.DataFrame
    alternatives: pd.DataFrame
    marginal_steps: pd.DataFrame


@dataclass(frozen=True)
class MarginalCoverage:
    """One possible coverage upgrade."""

    match_index: int
    next_size: int
    current_probability: float
    new_probability: float
    benefit_probability: float
    marginal_cost: float
    benefit_cost_ratio: float
    entropy: float
    top_gap: float


class TicketOptimizer:
    """Assign fixed, double and triple selections intelligently."""

    def __init__(self, game_config: GameConfig) -> None:
        self.game_config = game_config

    def optimize(
        self,
        predictions: list[MatchPrediction],
        budget: float,
        risk_profile: RiskProfile | str = RiskProfile.BALANCED,
        max_doubles: int | None = None,
        max_triples: int | None = None,
        goal: OptimizationGoal | str = OptimizationGoal.MAX_PROBABILITY,
    ) -> OptimizedTicket:
        """Build an optimized ticket."""

        risk_profile = RiskProfile(risk_profile)
        goal = OptimizationGoal(goal)
        max_doubles = self.game_config.max_doubles if max_doubles is None else max_doubles
        max_triples = self.game_config.max_triples if max_triples is None else max_triples
        selections = [[prediction.recommendation] for prediction in predictions]
        probabilities = [list(prediction.probabilities.values()) for prediction in predictions]
        option_order = list(self.game_config.options)
        marginal_steps: list[dict[str, Any]] = []
        while True:
            candidates = self._marginal_candidates(
                predictions=predictions,
                selections=selections,
                budget=budget,
                max_doubles=max_doubles,
                max_triples=max_triples,
                risk_profile=risk_profile,
                goal=goal,
            )
            if not candidates:
                break
            best = candidates[0]
            ranked = top_indices(probabilities[best.match_index], len(option_order))
            selections[best.match_index] = [option_order[position] for position in ranked[: best.next_size]]
            marginal_steps.append(
                {
                    "id": predictions[best.match_index].id,
                    "partido": f"{predictions[best.match_index].local} vs {predictions[best.match_index].visitante}",
                    "tamano_cobertura": best.next_size,
                    "beneficio_probabilistico": best.benefit_probability,
                    "costo_marginal": best.marginal_cost,
                    "ratio_beneficio_costo": best.benefit_cost_ratio,
                    "entropia": best.entropy,
                    "brecha_top1_top2": best.top_gap,
                }
            )
        selected_indexes = [
            [option_order.index(option) for option in selection] for selection in selections
        ]
        probability_all = cumulative_ticket_probability(probabilities, selected_indexes)
        table = self._build_table(predictions, selections, marginal_steps)
        alternatives = self._build_alternatives(predictions, budget)
        return OptimizedTicket(
            selections=selections,
            combinations=self.game_config.count_combinations(selections),
            cost=self.game_config.calculate_cost(selections),
            probability_all_correct=probability_all,
            table=table,
            alternatives=alternatives,
            marginal_steps=pd.DataFrame(marginal_steps),
        )

    def enumerate_lines(self, selections: list[list[str]], limit: int = 5000) -> list[tuple[str, ...]]:
        """Enumerate concrete simple tickets represented by selections."""

        combos = self.game_config.count_combinations(selections)
        if combos > limit:
            raise ValueError(f"Ticket has {combos} lines, above enumeration limit {limit}.")
        return list(product(*selections))

    def _rank_candidates(
        self,
        predictions: list[MatchPrediction],
        goal: OptimizationGoal,
        risk_profile: RiskProfile,
    ) -> list[int]:
        scores = []
        for idx, prediction in enumerate(predictions):
            probs = list(prediction.probabilities.values())
            uncertainty = entropy(probs)
            upset_value = sorted(probs, reverse=True)[1]
            max_prob = max(probs)
            if goal == OptimizationGoal.MIN_COST:
                score = uncertainty * 0.4 + upset_value * 0.2
            elif goal == OptimizationGoal.MAX_UNCERTAINTY_COVERAGE:
                score = uncertainty
            elif goal == OptimizationGoal.MAX_EXPECTED_VALUE:
                score = uncertainty * 0.5 + upset_value * 0.5
            else:
                score = uncertainty * 0.7 + (1 - max_prob) * 0.3
            if risk_profile == RiskProfile.CONSERVATIVE:
                score *= 0.85
            elif risk_profile == RiskProfile.AGGRESSIVE:
                score *= 1.15
            scores.append((idx, score))
        return [idx for idx, _ in sorted(scores, key=lambda item: item[1], reverse=True)]

    def _marginal_candidates(
        self,
        predictions: list[MatchPrediction],
        selections: list[list[str]],
        budget: float,
        max_doubles: int,
        max_triples: int,
        risk_profile: RiskProfile,
        goal: OptimizationGoal,
    ) -> list[MarginalCoverage]:
        current_probability = self._accumulated_probability(predictions, selections)
        current_cost = self.game_config.calculate_cost(selections)
        current_doubles = sum(1 for selection in selections if len(selection) == 2)
        current_triples = sum(1 for selection in selections if len(selection) == 3)
        candidates: list[MarginalCoverage] = []
        for idx, prediction in enumerate(predictions):
            current_size = len(selections[idx])
            if current_size >= len(self.game_config.options):
                continue
            next_size = current_size + 1
            if next_size == 2 and current_doubles >= max_doubles:
                continue
            if next_size == 3 and current_triples >= max_triples:
                continue
            if not self._is_allowed_by_profile(prediction, next_size, risk_profile, goal):
                continue
            proposed = [item[:] for item in selections]
            probs = list(prediction.probabilities.values())
            ranked = top_indices(probs, len(probs))
            proposed[idx] = [self.game_config.options[position] for position in ranked[:next_size]]
            new_cost = self.game_config.calculate_cost(proposed)
            if new_cost > budget:
                continue
            new_probability = self._accumulated_probability(predictions, proposed)
            benefit = new_probability - current_probability
            marginal_cost = new_cost - current_cost
            if marginal_cost <= 0 or benefit <= 0:
                continue
            sorted_probs = sorted(probs, reverse=True)
            top_gap = sorted_probs[0] - sorted_probs[1]
            uncertainty = entropy(probs)
            ratio = benefit / marginal_cost
            ratio *= self._goal_multiplier(goal, uncertainty, top_gap, next_size)
            candidates.append(
                MarginalCoverage(
                    match_index=idx,
                    next_size=next_size,
                    current_probability=current_probability,
                    new_probability=new_probability,
                    benefit_probability=benefit,
                    marginal_cost=marginal_cost,
                    benefit_cost_ratio=ratio,
                    entropy=uncertainty,
                    top_gap=top_gap,
                )
            )
        return sorted(candidates, key=lambda item: item.benefit_cost_ratio, reverse=True)

    def _is_allowed_by_profile(
        self,
        prediction: MatchPrediction,
        next_size: int,
        risk_profile: RiskProfile,
        goal: OptimizationGoal,
    ) -> bool:
        probs = list(prediction.probabilities.values())
        uncertainty = entropy(probs)
        sorted_probs = sorted(probs, reverse=True)
        top_gap = sorted_probs[0] - sorted_probs[1]
        third_gap = sorted_probs[1] - sorted_probs[2] if len(sorted_probs) > 2 else 1.0
        if risk_profile == RiskProfile.CONSERVATIVE:
            return next_size == 2 and (
                uncertainty >= HIGH_UNCERTAINTY_ENTROPY or top_gap <= CLOSE_GAME_GAP
            )
        if risk_profile == RiskProfile.BALANCED:
            if next_size == 3:
                return uncertainty >= 0.97 and top_gap <= EXTREME_UNCERTAINTY_GAP and third_gap <= 0.08
            return uncertainty >= 0.86 or top_gap <= 0.16
        if goal == OptimizationGoal.MIN_COST:
            return uncertainty >= HIGH_UNCERTAINTY_ENTROPY or top_gap <= CLOSE_GAME_GAP
        return True

    @staticmethod
    def _goal_multiplier(
        goal: OptimizationGoal,
        uncertainty: float,
        top_gap: float,
        next_size: int,
    ) -> float:
        if goal == OptimizationGoal.MAX_UNCERTAINTY_COVERAGE:
            return 1 + uncertainty
        if goal == OptimizationGoal.MAX_EXPECTED_VALUE:
            return 1 + (uncertainty * 0.5) + max(0.0, CLOSE_GAME_GAP - top_gap)
        if goal == OptimizationGoal.MIN_COST:
            return 1 + max(0.0, uncertainty - 0.85)
        return 1 + (0.2 if next_size == 2 else 0.1)

    def _accumulated_probability(
        self,
        predictions: list[MatchPrediction],
        selections: list[list[str]],
    ) -> float:
        option_order = list(self.game_config.options)
        probabilities = [list(prediction.probabilities.values()) for prediction in predictions]
        selected_indexes = [
            [option_order.index(option) for option in selection] for selection in selections
        ]
        return cumulative_ticket_probability(probabilities, selected_indexes)

    def _build_table(
        self,
        predictions: list[MatchPrediction],
        selections: list[list[str]],
        marginal_steps: list[dict[str, Any]],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        covered_ids = {int(step["id"]): step for step in marginal_steps}
        for prediction, selection in zip(predictions, selections, strict=True):
            probs = list(prediction.probabilities.values())
            sorted_probs = sorted(probs, reverse=True)
            main_probability = prediction.probabilities[prediction.recommendation]
            selected_probability = sum(prediction.probabilities[item] for item in selection)
            uncertainty = entropy(probs)
            top_gap = sorted_probs[0] - sorted_probs[1]
            if prediction.id in covered_ids:
                step = covered_ids[prediction.id]
                reason = (
                    "Cubierto por mejor ratio beneficio/costo; "
                    f"entropia {step['entropia']:.2f}, brecha {step['brecha_top1_top2']:.1%}."
                )
            elif uncertainty >= HIGH_UNCERTAINTY_ENTROPY or top_gap <= CLOSE_GAME_GAP:
                reason = "Candidato incierto, pero otra cobertura dio mejor beneficio por costo o no cupo en presupuesto."
            else:
                reason = "No cubierto: favorito suficientemente claro para controlar costo."
            rows.append(
                {
                    "id": prediction.id,
                    "partido": f"{prediction.local} vs {prediction.visitante}",
                    "seleccion_fija": prediction.recommendation,
                    "cobertura_recomendada": "/".join(selection),
                    "probabilidad_principal": main_probability,
                    "probabilidad_cubierta": selected_probability,
                    "probabilidad_acumulada_quiniela": self._accumulated_probability(predictions, selections),
                    "entropia": uncertainty,
                    "brecha_top1_top2": top_gap,
                    "confianza": prediction.confidence,
                    "riesgo": prediction.risk,
                    "motivo_cobertura": reason,
                    "justificacion": prediction.explanation,
                }
            )
        return pd.DataFrame(rows)

    def _build_alternatives(self, predictions: list[MatchPrediction], budget: float) -> pd.DataFrame:
        rows = []
        for name, doubles, triples in [
            ("Solo favoritos", 0, 0),
            ("Cobertura ligera", 3, 0),
            ("Balanceada", 5, 1),
            ("Agresiva", 6, 2),
        ]:
            max_d = min(doubles, self.game_config.max_doubles or doubles)
            max_t = min(triples, self.game_config.max_triples or triples)
            selections = self._quick_strategy_selections(predictions, budget, max_d, max_t)
            combinations = self.game_config.count_combinations(selections)
            cost = self.game_config.calculate_cost(selections)
            option_order = list(self.game_config.options)
            probabilities = [list(prediction.probabilities.values()) for prediction in predictions]
            selected_indexes = [
                [option_order.index(option) for option in selection] for selection in selections
            ]
            prob = cumulative_ticket_probability(probabilities, selected_indexes)
            rows.append(
                {
                    "estrategia": name,
                    "combinaciones": combinations,
                    "costo": cost,
                    "prob_quiniela_completa": prob,
                }
            )
        return pd.DataFrame(rows).sort_values("prob_quiniela_completa", ascending=False)

    def _quick_strategy_selections(
        self,
        predictions: list[MatchPrediction],
        budget: float,
        max_doubles: int,
        max_triples: int,
    ) -> list[list[str]]:
        selections = [[prediction.recommendation] for prediction in predictions]
        option_order = list(self.game_config.options)
        budget_combinations = max(int(budget // self.game_config.cost_per_combination), 1)
        ranked = sorted(
            range(len(predictions)),
            key=lambda idx: entropy(list(predictions[idx].probabilities.values())),
            reverse=True,
        )
        doubles = triples = 0
        for idx in ranked:
            probs = list(predictions[idx].probabilities.values())
            top = [option_order[pos] for pos in top_indices(probs, len(probs))]
            target_size = 1
            if doubles < max_doubles:
                target_size = 2
            if triples < max_triples and doubles >= max_doubles:
                target_size = 3
            if target_size == 1:
                continue
            old = selections[idx]
            selections[idx] = top[:target_size]
            if self.game_config.count_combinations(selections) > budget_combinations:
                selections[idx] = old
                continue
            if target_size == 2:
                doubles += 1
            if target_size == 3:
                triples += 1
        return selections
