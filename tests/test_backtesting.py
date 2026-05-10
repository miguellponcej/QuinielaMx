import pandas as pd

from src.backtesting.backtester import compare_baselines
from src.config.games import GameType, get_game_config


def test_compare_baselines_returns_requested_strategies():
    frame = pd.read_csv("data/examples/progol_backtest_sample.csv")
    history = pd.read_csv("data/examples/progol_historical_results_long.csv")
    soccer = pd.read_csv("data/examples/match_results_soccer.csv")
    config = get_game_config(GameType.PROGOL)

    comparison = compare_baselines(frame, config, historical_frequency_frame=history, soccer_results=soccer)

    strategies = set(comparison["estrategia"])
    assert "Siempre local" in strategies
    assert "Favorito mercado" in strategies
    assert "Frecuencia historica" in strategies
    assert "Aleatorio" in strategies
    assert "Elo" in strategies
    assert "Ensamble" in strategies
    assert comparison[["accuracy", "log_loss", "brier_score"]].notna().all().all()

