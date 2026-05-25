"""Audited real-time prediction pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.audit.provenance import PredictionTrace
from src.config.games import GameConfig, GameType, RiskProfile, get_game_config
from src.history.learning import apply_historical_learning
from src.optimization.ticket_optimizer import OptimizedTicket, TicketOptimizer
from src.prediction.predictor import MatchPrediction, QuinielaPredictor


@dataclass(frozen=True)
class RealTimePredictionResult:
    """Complete result emitted by the audited prediction pipeline."""

    game_config: GameConfig
    predictions: list[MatchPrediction]
    prediction_frame: pd.DataFrame
    ticket: OptimizedTicket | None
    trace: PredictionTrace
    data_quality_notes: list[str]


def real_time_prediction_pipeline(
    game_type: GameType | str,
    quiniela: list[dict[str, Any]] | pd.DataFrame,
    trace: PredictionTrace,
    market_probs: pd.DataFrame | None = None,
    budget: float | None = None,
    risk_profile: RiskProfile | str = RiskProfile.BALANCED,
    n_matches: int | None = None,
) -> RealTimePredictionResult:
    """Generate audited predictions and optional optimized ticket.

    All app-facing prediction flows should enter here so traceability and
    input validation stay consistent.
    """

    trace.validate_ready()
    frame = pd.DataFrame(quiniela).copy()
    if frame.empty:
        raise ValueError("La quiniela no contiene partidos para predecir.")
    config = get_game_config(game_type, n_matches=n_matches or len(frame))
    _validate_quiniela_frame(frame)
    predictor = QuinielaPredictor(game_type=config.game_type, n_matches=len(frame))
    market_frame = market_probs if market_probs is not None else _market_frame_from_quiniela(frame, config)
    predictions = predictor.predict(frame, market_probs=market_frame, trace=trace)
    learning_context = apply_historical_learning(predictions, _game_id(config.game_type))
    prediction_frame = predictor.to_dataframe(predictions)
    ticket = None
    if budget is not None:
        ticket = TicketOptimizer(config).optimize(predictions, budget=budget, risk_profile=risk_profile)
    return RealTimePredictionResult(
        game_config=config,
        predictions=predictions,
        prediction_frame=prediction_frame,
        ticket=ticket,
        trace=trace,
        data_quality_notes=_quality_notes(frame, trace, learning_context),
    )


def _validate_quiniela_frame(frame: pd.DataFrame) -> None:
    required = {"id", "local", "visitante", "liga", "fecha"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Faltan columnas requeridas en la quiniela: {', '.join(missing)}.")
    empty_teams = frame["local"].isna() | frame["visitante"].isna() | (frame["local"].astype(str).str.strip() == "") | (
        frame["visitante"].astype(str).str.strip() == ""
    )
    if bool(empty_teams.any()):
        raise ValueError("Todos los partidos deben tener equipo local y visitante.")


def _quality_notes(frame: pd.DataFrame, trace: PredictionTrace, learning_context: dict | None = None) -> list[str]:
    notes = [f"Partidos cargados: {len(frame)}."]
    if trace.incomplete_data:
        notes.append("Hay datos incompletos registrados; la confianza debe interpretarse con cautela.")
    if not trace.fresh_data:
        notes.append("No se confirmo frescura completa de datos externos.")
    if learning_context:
        notes.append(f"Aprendizaje historico: {learning_context.get('message')} Muestra={learning_context.get('sample_size')}.")
    return notes


def _game_id(game_type: GameType) -> str:
    return {
        GameType.PROGOL: "progol",
        GameType.PROGOL_REVANCHA: "progol_revancha",
        GameType.PROGOL_MEDIA_SEMANA: "progol_media_semana",
        GameType.PROTOUCH: "protouch",
        GameType.RANDOM_DRAW: "random_draw",
    }[game_type]


def _market_frame_from_quiniela(frame: pd.DataFrame, config: GameConfig) -> pd.DataFrame | None:
    """Extract embedded market columns from a web-provided quiniela frame."""

    columns = {str(column).lower() for column in frame.columns}
    option_suffixes = [option.lower() for option in config.options]
    has_probabilities = all(f"prob_{suffix}" in columns for suffix in option_suffixes)
    has_decimal_odds = all((f"momio_{suffix}" in columns or f"odds_{suffix}" in columns) for suffix in option_suffixes)
    has_american_odds = all(f"american_{suffix}" in columns or f"momio_americano_{suffix}" in columns for suffix in option_suffixes)
    has_market_notes = bool(
        columns
        & {
            "fuente_momio",
            "fuente",
            "odds_source",
            "source",
            "bookmaker",
            "casa",
            "casa_apuestas",
            "linea_mercado",
            "market_line",
            "momio_texto",
            "odds_details",
        }
    )
    if not (has_probabilities or has_decimal_odds or has_american_odds or has_market_notes):
        return None
    keep = [
        column
        for column in frame.columns
        if str(column).lower() == "id"
        or str(column).lower().startswith(("prob_", "momio_", "odds_", "decimal_", "american_"))
        or str(column).lower()
        in {
            "fuente_momio",
            "fuente",
            "odds_source",
            "source",
            "bookmaker",
            "casa",
            "casa_apuestas",
            "linea_mercado",
            "market_line",
            "momio_texto",
            "odds_details",
        }
    ]
    return frame[keep].copy()
