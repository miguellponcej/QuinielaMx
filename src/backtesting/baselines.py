"""Baseline strategies for quiniela model comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config.games import GameConfig
from src.models.elo import EloModel
from src.models.ensemble import weighted_ensemble
from src.models.poisson_soccer import PoissonSoccerModel


def always_local(frame: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Baseline that always chooses local."""

    return _constant_prediction(frame, game_config, "L")


def market_favorite(frame: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Baseline that chooses the highest market probability."""

    prob_cols = [f"prob_{option.lower()}" for option in game_config.options]
    _require_columns(frame, prob_cols)
    rows = []
    for row in frame.itertuples(index=False):
        probs = {option: float(getattr(row, f"prob_{option.lower()}")) for option in game_config.options}
        rows.append({"prediccion": max(probs, key=probs.get), **_prob_columns(probs)})
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def historical_frequency(
    frame: pd.DataFrame,
    game_config: GameConfig,
    history: pd.DataFrame,
) -> pd.DataFrame:
    """Baseline from historical outcome frequencies by position."""

    _require_columns(history, {"posicion", "resultado"})
    rows = []
    global_probs = _frequency_probs(history["resultado"], game_config)
    for row in frame.itertuples(index=False):
        position = int(getattr(row, "id", getattr(row, "posicion", 0)))
        subset = history.loc[history["posicion"] == position, "resultado"]
        probs = _frequency_probs(subset, game_config) if not subset.empty else global_probs
        rows.append({"prediccion": max(probs, key=probs.get), **_prob_columns(probs)})
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def random_strategy(
    frame: pd.DataFrame,
    game_config: GameConfig,
    seed: int = 42,
) -> pd.DataFrame:
    """Uniform random baseline."""

    rng = np.random.default_rng(seed)
    uniform = {option: 1 / len(game_config.options) for option in game_config.options}
    rows = []
    for _ in range(len(frame)):
        rows.append(
            {
                "prediccion": str(rng.choice(game_config.options)),
                **_prob_columns(uniform),
            }
        )
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def elo_strategy(
    frame: pd.DataFrame,
    game_config: GameConfig,
    results: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Elo baseline for soccer-style 1X2 games."""

    model = EloModel()
    if results is not None and not results.empty:
        model.fit(results)
    rows = []
    for row in frame.itertuples(index=False):
        home = str(getattr(row, "local"))
        away = str(getattr(row, "visitante"))
        home_prob = model.predict_home_win(home, away)
        if "E" in game_config.options:
            probs = {"L": home_prob * 0.78, "E": 0.22, "V": (1 - home_prob) * 0.78}
        else:
            probs = {"L": home_prob, "V": 1 - home_prob}
        probs = _normalize(probs)
        rows.append({"prediccion": max(probs, key=probs.get), **_prob_columns(probs)})
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def ensemble_strategy(
    frame: pd.DataFrame,
    game_config: GameConfig,
    soccer_results: pd.DataFrame | None = None,
    market_weight: float = 0.55,
) -> pd.DataFrame:
    """Simple ensemble baseline using Elo, Poisson and market probabilities when available."""

    elo = EloModel()
    poisson = PoissonSoccerModel()
    if soccer_results is not None and not soccer_results.empty:
        elo.fit(soccer_results)
        poisson.fit(soccer_results)
    has_market = all(f"prob_{option.lower()}" in frame.columns for option in game_config.options)
    rows = []
    for row in frame.itertuples(index=False):
        home = str(getattr(row, "local"))
        away = str(getattr(row, "visitante"))
        home_prob = elo.predict_home_win(home, away)
        elo_probs = {"L": home_prob * 0.78, "E": 0.22, "V": (1 - home_prob) * 0.78}
        models = [_normalize(elo_probs), poisson.predict(home, away)]
        weights = [0.25, 0.35]
        if has_market:
            market = {option: float(getattr(row, f"prob_{option.lower()}")) for option in game_config.options}
            models.append(_normalize(market))
            weights.append(market_weight)
        probs = weighted_ensemble(models, weights)
        rows.append({"prediccion": max(probs, key=probs.get), **_prob_columns(probs)})
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def _constant_prediction(frame: pd.DataFrame, game_config: GameConfig, outcome: str) -> pd.DataFrame:
    if outcome not in game_config.options:
        outcome = game_config.options[0]
    probs = {option: 0.0 for option in game_config.options}
    probs[outcome] = 1.0
    rows = [{"prediccion": outcome, **_prob_columns(probs)} for _ in range(len(frame))]
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def _frequency_probs(values: pd.Series, game_config: GameConfig) -> dict[str, float]:
    counts = values.astype(str).str.upper().value_counts().to_dict()
    total = sum(counts.get(option, 0) for option in game_config.options)
    if total == 0:
        return {option: 1 / len(game_config.options) for option in game_config.options}
    return {option: counts.get(option, 0) / total for option in game_config.options}


def _normalize(probs: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in probs.values())
    if total <= 0:
        return {key: 1 / len(probs) for key in probs}
    return {key: max(value, 0.0) / total for key, value in probs.items()}


def _prob_columns(probs: dict[str, float]) -> dict[str, float]:
    return {f"prob_{key.lower()}": value for key, value in probs.items()}


def _require_columns(frame: pd.DataFrame, columns: set[str] | list[str]) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

