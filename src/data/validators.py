"""Input validators."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.config.games import GameConfig


REQUIRED_QUINIELA_COLUMNS = {"id", "local", "visitante", "liga", "fecha"}
REQUIRED_SOCCER_RESULT_COLUMNS = {"fecha", "local", "visitante", "goles_local", "goles_visitante"}
REQUIRED_FOOTBALL_RESULT_COLUMNS = {"fecha", "local", "visitante", "puntos_local", "puntos_visitante"}
REQUIRED_HISTORICAL_QUINIELA_COLUMNS = {"sorteo", "fecha", "resultado"}


def validate_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    """Raise a clear error when required columns are missing."""

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def validate_quiniela_df(df: pd.DataFrame, game_config: GameConfig) -> None:
    """Validate a quiniela table against a game config."""

    validate_columns(df, REQUIRED_QUINIELA_COLUMNS)
    if len(df) != game_config.n_matches:
        raise ValueError(
            f"{game_config.name} requires {game_config.n_matches} matches; got {len(df)}."
        )
    if df[["local", "visitante"]].isna().any().any():
        raise ValueError("Local and visitante fields cannot be empty.")
    empty_mask = df[["local", "visitante"]].astype(str).apply(lambda col: col.str.strip().eq(""))
    if empty_mask.any().any():
        raise ValueError("Local and visitante fields cannot be blank.")


def validate_probability_columns(df: pd.DataFrame, options: tuple[str, ...]) -> None:
    """Validate probability columns and row sums."""

    columns = [f"prob_{option.lower()}" for option in options]
    validate_columns(df, columns)
    sums = df[columns].sum(axis=1)
    if not sums.between(0.99, 1.01).all():
        raise ValueError("Probability columns must sum to 1 per row.")


def validate_market_probabilities(df: pd.DataFrame, game_config: GameConfig) -> None:
    """Validate market probability file for a selected game."""

    validate_columns(df, {"id"})
    validate_probability_columns(df, game_config.options)
    if len(df) != game_config.n_matches:
        raise ValueError(
            f"{game_config.name} requires {game_config.n_matches} probability rows; got {len(df)}."
        )
    probability_cols = [f"prob_{option.lower()}" for option in game_config.options]
    if (df[probability_cols] < 0).any().any():
        raise ValueError("Probabilities cannot be negative.")


def validate_soccer_results(df: pd.DataFrame) -> None:
    """Validate historical soccer results."""

    validate_columns(df, REQUIRED_SOCCER_RESULT_COLUMNS)
    _validate_team_columns(df)
    if (df[["goles_local", "goles_visitante"]] < 0).any().any():
        raise ValueError("Soccer goals cannot be negative.")


def validate_american_football_results(df: pd.DataFrame) -> None:
    """Validate historical NFL/NCAA results."""

    validate_columns(df, REQUIRED_FOOTBALL_RESULT_COLUMNS)
    _validate_team_columns(df)
    if (df[["puntos_local", "puntos_visitante"]] < 0).any().any():
        raise ValueError("Football points cannot be negative.")


def validate_historical_quiniela_results(df: pd.DataFrame, game_config: GameConfig) -> None:
    """Validate historical official quiniela results."""

    validate_columns(df, REQUIRED_HISTORICAL_QUINIELA_COLUMNS)
    allowed = set(game_config.options)
    for row in df.itertuples(index=False):
        result = str(getattr(row, "resultado")).replace(" ", "").upper()
        if len(result) != game_config.n_matches:
            raise ValueError(
                f"Historical result {getattr(row, 'sorteo')} must have {game_config.n_matches} outcomes."
            )
        invalid = set(result) - allowed
        if invalid:
            raise ValueError(f"Invalid historical result outcomes: {sorted(invalid)}.")


def validate_ticket_budget(game_config: GameConfig, selections: list[list[str]], budget: float) -> None:
    """Validate that a ticket cost is correctly calculated and affordable."""

    game_config.validate_ticket(selections)
    combinations = game_config.count_combinations(selections)
    expected_cost = combinations * game_config.cost_per_combination
    actual_cost = game_config.calculate_cost(selections)
    if abs(expected_cost - actual_cost) > 1e-9:
        raise ValueError("Ticket cost calculation mismatch.")
    if actual_cost > budget:
        raise ValueError(f"Budget {budget} does not cover ticket cost {actual_cost}.")


def _validate_team_columns(df: pd.DataFrame) -> None:
    if df[["local", "visitante"]].isna().any().any():
        raise ValueError("All rows must include local and visitante.")
    empty_mask = df[["local", "visitante"]].astype(str).apply(lambda col: col.str.strip().eq(""))
    if empty_mask.any().any():
        raise ValueError("Team names cannot be blank.")
