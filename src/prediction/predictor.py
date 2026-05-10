"""Prediction engine for quiniela rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.audit.provenance import PredictionTrace, TraceValidationError
from src.config.games import GameConfig, GameType, get_game_config
from src.models.dixon_coles import adjust_low_scoring_draws
from src.models.elo import EloModel
from src.models.ensemble import weighted_ensemble
from src.models.nfl_model import NFLMarginModel
from src.models.poisson_soccer import PoissonSoccerModel
from src.prediction.confidence import confidence_label, risk_score
from src.prediction.explanations import ExecutiveExplanation, build_executive_explanation
from src.utils.odds import american_to_decimal, remove_vig
from src.utils.probability import normalize_probabilities, top_indices


@dataclass
class MatchPrediction:
    """Prediction output for one match."""

    id: int
    local: str
    visitante: str
    liga: str
    fecha: str
    probabilities: dict[str, float]
    recommendation: str
    confidence: str
    coverage: list[str]
    coverage_type: str
    risk: float
    explanation: str
    executive_explanation: ExecutiveExplanation
    cost_impact: int
    trace: PredictionTrace
    market_odds: dict[str, float]
    market_source: str

    def as_dict(self) -> dict[str, Any]:
        """Return serializable dict."""

        row = {
            "id": self.id,
            "local": self.local,
            "visitante": self.visitante,
            "liga": self.liga,
            "fecha": self.fecha,
            "recomendacion": self.recommendation,
            "confianza": self.confidence,
            "cobertura": "/".join(self.coverage),
            "tipo_cobertura": self.coverage_type,
            "riesgo": self.risk,
            "impacto_costo": self.cost_impact,
            "explicacion": self.explanation,
            "lectura_rapida": self.executive_explanation.lectura_rapida,
            "factores": self.executive_explanation.factores,
            "recomendacion_final": self.executive_explanation.recomendacion_final,
            "mensaje_ejecutivo": self.executive_explanation.mensaje,
            "momios": _format_odds(self.market_odds),
            "fuente_momio": self.market_source or "Dato no disponible",
            "mercado_disponible": "Si" if self.market_odds or self.market_source else "No",
            "trazabilidad": self.trace.as_dict(),
            **self.trace.compact_summary(),
        }
        for key, value in self.executive_explanation.lectura_rapida.items():
            row[f"lectura_{key}"] = value
        for key, value in self.executive_explanation.factores.items():
            row[f"factor_{key}"] = value
        for key, value in self.probabilities.items():
            row[f"prob_{key.lower()}"] = value
        for key, value in self.market_odds.items():
            row[f"momio_{key.lower()}"] = value
        return row


class QuinielaPredictor:
    """Predict match probabilities and recommended coverage."""

    def __init__(
        self,
        game_type: GameType | str,
        soccer_model: PoissonSoccerModel | None = None,
        elo_model: EloModel | None = None,
        nfl_model: NFLMarginModel | None = None,
        n_matches: int | None = None,
    ) -> None:
        self.game_config: GameConfig = get_game_config(game_type, n_matches=n_matches)
        self.game_type = self.game_config.game_type
        self.soccer_model = soccer_model or PoissonSoccerModel()
        self.elo_model = elo_model or EloModel()
        self.nfl_model = nfl_model or NFLMarginModel()

    def predict(
        self,
        quiniela: list[dict[str, Any]] | pd.DataFrame,
        market_probs: pd.DataFrame | None = None,
        trace: PredictionTrace | None = None,
    ) -> list[MatchPrediction]:
        """Predict all matches in a quiniela."""

        if trace is None:
            raise TraceValidationError(
                "Prediction blocked: traceability context is required before generating probabilities."
            )
        trace.validate_ready()
        frame = pd.DataFrame(quiniela).copy()
        if len(frame) != self.game_config.n_matches:
            raise ValueError(
                f"{self.game_config.name} requires {self.game_config.n_matches} matches; got {len(frame)}."
            )
        market_lookup = self._market_lookup(market_probs)
        predictions: list[MatchPrediction] = []
        for row in frame.itertuples(index=False):
            match_id = int(getattr(row, "id"))
            local = str(getattr(row, "local"))
            visitante = str(getattr(row, "visitante"))
            liga = str(getattr(row, "liga"))
            fecha = str(getattr(row, "fecha"))
            probs = self._predict_match(match_id, local, visitante, market_lookup)
            market_info = market_lookup.get(match_id, {})
            market_odds = dict(market_info.get("odds", {}))
            market_source = str(market_info.get("source", ""))
            recommendation = max(probs, key=probs.get)
            coverage = self._suggest_initial_coverage(probs)
            coverage_type = {1: "Fijo", 2: "Doble", 3: "Triple"}[len(coverage)]
            executive_explanation = build_executive_explanation(
                self.game_type,
                local,
                visitante,
                probs,
                recommendation,
                coverage,
                has_market=match_id in market_lookup,
            )
            explanation = executive_explanation.mensaje
            predictions.append(
                MatchPrediction(
                    id=match_id,
                    local=local,
                    visitante=visitante,
                    liga=liga,
                    fecha=fecha,
                    probabilities=probs,
                    recommendation=recommendation,
                    confidence=confidence_label(list(probs.values())),
                    coverage=coverage,
                    coverage_type=coverage_type,
                    risk=risk_score(list(probs.values())),
                    explanation=explanation,
                    executive_explanation=executive_explanation,
                    cost_impact=len(coverage),
                    trace=trace,
                    market_odds=market_odds,
                    market_source=market_source,
                )
            )
        return predictions

    def to_dataframe(self, predictions: list[MatchPrediction]) -> pd.DataFrame:
        """Convert predictions to DataFrame."""

        return pd.DataFrame([prediction.as_dict() for prediction in predictions])

    def _market_lookup(self, market_probs: pd.DataFrame | None) -> dict[int, dict[str, Any]]:
        if market_probs is None or market_probs.empty:
            return {}
        frame = market_probs.copy()
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        lookup: dict[int, dict[str, Any]] = {}
        for _, row in frame.iterrows():
            row_data = {str(key).strip().lower(): value for key, value in row.to_dict().items()}
            match_id = int(row_data.get("id", row_data.get("posicion", 0)))
            odds = _extract_decimal_odds(row_data, self.game_config.options)
            probabilities = _extract_market_probabilities(row_data, self.game_config.options, odds)
            source = _extract_market_source(row_data)
            if probabilities:
                lookup[match_id] = {
                    "probabilities": probabilities,
                    "odds": odds,
                    "source": source,
                }
        return lookup

    def _predict_match(
        self,
        match_id: int,
        local: str,
        visitante: str,
        market_lookup: dict[int, dict[str, Any]],
    ) -> dict[str, float]:
        if match_id in market_lookup:
            market = market_lookup[match_id].get("probabilities")
        else:
            market = None
        if self.game_type == GameType.PROTOUCH:
            base = self.nfl_model.predict_from_spread()
            return weighted_ensemble([base, market], [0.45, 0.55]) if market else base
        poisson_probs = self.soccer_model.predict(local, visitante)
        poisson_probs = adjust_low_scoring_draws(poisson_probs)
        elo_home = self.elo_model.predict_home_win(local, visitante)
        elo_probs = {"L": elo_home * 0.78, "E": 0.22, "V": (1 - elo_home) * 0.78}
        weights = [0.55, 0.20]
        models = [poisson_probs, elo_probs]
        if market:
            models.append(market)
            weights.append(0.55)
        return weighted_ensemble(models, weights)

    def _suggest_initial_coverage(self, probabilities: dict[str, float]) -> list[str]:
        values = list(probabilities.values())
        indexes = top_indices(values, len(values))
        ordered_options = [self.game_config.options[index] for index in indexes]
        risk = risk_score(values)
        if risk >= 0.55:
            return ordered_options[:3]
        if risk >= 0.42:
            return ordered_options[:2]
        return ordered_options[:1]
def _extract_decimal_odds(row: dict[str, Any], options: tuple[str, ...]) -> dict[str, float]:
    odds: dict[str, float] = {}
    for option in options:
        suffix = option.lower()
        value = _first_present(row, [f"momio_{suffix}", f"odds_{suffix}", f"decimal_{suffix}"])
        american = _first_present(row, [f"american_{suffix}", f"momio_americano_{suffix}"])
        if value is not None:
            odds[option] = float(value)
        elif american is not None:
            odds[option] = american_to_decimal(float(american))
    return odds


def _extract_market_probabilities(
    row: dict[str, Any],
    options: tuple[str, ...],
    odds: dict[str, float],
) -> dict[str, float]:
    values = []
    for option in options:
        value = _first_present(row, [f"prob_{option.lower()}"])
        if value is None:
            values = []
            break
        values.append(float(value))
    if values:
        normalized = normalize_probabilities(values)
        return dict(zip(options, map(float, normalized), strict=True))
    if set(odds) == set(options):
        return remove_vig(odds)
    return {}


def _extract_market_source(row: dict[str, Any]) -> str:
    value = _first_present(
        row,
        ["fuente_momio", "fuente", "odds_source", "source", "bookmaker", "casa", "casa_apuestas"],
    )
    return "" if value is None else str(value)


def _first_present(row: dict[str, Any], keys: list[str]) -> Any | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        if pd.isna(value):
            continue
        if value not in (None, ""):
            return value
    return None


def _format_odds(odds: dict[str, float]) -> str:
    if not odds:
        return "Dato no disponible"
    return " | ".join(f"{option}: {value:.2f}" for option, value in odds.items())
