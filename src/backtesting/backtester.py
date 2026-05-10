"""Historical model evaluation."""

from __future__ import annotations

import pandas as pd

from src.backtesting.baselines import (
    always_local,
    elo_strategy,
    ensemble_strategy,
    historical_frequency,
    market_favorite,
    random_strategy,
)
from src.backtesting.metrics import multiclass_accuracy, multiclass_brier_score, multiclass_log_loss
from src.config.games import GameConfig


def evaluate_prediction_frame(
    frame: pd.DataFrame,
    labels: list[str],
    actual_col: str = "resultado",
    pred_col: str = "prediccion",
) -> dict[str, float]:
    """Evaluate a prediction DataFrame."""

    prob_cols = [f"prob_{label.lower()}" for label in labels]
    required = [actual_col, pred_col, *prob_cols]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns for backtesting: {missing}")
    probabilities = frame[prob_cols].to_numpy(dtype=float)
    y_true = frame[actual_col].astype(str).tolist()
    y_pred = frame[pred_col].astype(str).tolist()
    return {
        "accuracy": multiclass_accuracy(y_true, y_pred),
        "log_loss": multiclass_log_loss(y_true, probabilities, labels),
        "brier_score": multiclass_brier_score(y_true, probabilities, labels),
    }


def compare_baselines(
    evaluation_frame: pd.DataFrame,
    game_config: GameConfig,
    historical_frequency_frame: pd.DataFrame | None = None,
    soccer_results: pd.DataFrame | None = None,
    actual_col: str = "resultado",
) -> pd.DataFrame:
    """Compare model against local, market, frequency, random, Elo and ensemble baselines."""

    labels = list(game_config.options)
    strategies: list[tuple[str, pd.DataFrame]] = [
        ("Siempre local", always_local(evaluation_frame, game_config)),
        ("Aleatorio", random_strategy(evaluation_frame, game_config)),
        ("Elo", elo_strategy(evaluation_frame, game_config, soccer_results)),
        ("Ensamble", ensemble_strategy(evaluation_frame, game_config, soccer_results)),
    ]
    if all(f"prob_{label.lower()}" in evaluation_frame.columns for label in labels):
        strategies.insert(1, ("Favorito mercado", market_favorite(evaluation_frame, game_config)))
    if historical_frequency_frame is not None and not historical_frequency_frame.empty:
        strategies.insert(
            2,
            ("Frecuencia historica", historical_frequency(evaluation_frame, game_config, historical_frequency_frame)),
        )
    rows = []
    for name, frame in strategies:
        test_frame = frame.copy()
        test_frame[actual_col] = evaluation_frame[actual_col].values
        metrics = evaluate_prediction_frame(
            test_frame,
            labels=labels,
            actual_col=actual_col,
            pred_col="prediccion",
        )
        rows.append({"estrategia": name, **metrics})
    return pd.DataFrame(rows).sort_values(["log_loss", "brier_score"], ascending=True)
