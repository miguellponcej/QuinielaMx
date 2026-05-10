"""Game configuration and cost rules."""

from __future__ import annotations

from enum import Enum
from functools import reduce
from operator import mul

from pydantic import BaseModel, Field, field_validator


class GameType(str, Enum):
    """Supported game types."""

    PROGOL = "progol"
    PROGOL_REVANCHA = "progol_revancha"
    PROGOL_MEDIA_SEMANA = "progol_media_semana"
    PROTOUCH = "protouch"
    RANDOM_DRAW = "random_draw"


class RiskProfile(str, Enum):
    """Optimization risk profile."""

    CONSERVATIVE = "conservador"
    BALANCED = "balanceado"
    AGGRESSIVE = "agresivo"


class OptimizationGoal(str, Enum):
    """Ticket optimization objective."""

    MAX_PROBABILITY = "maximizar_probabilidad"
    MAX_EXPECTED_VALUE = "maximizar_valor_esperado"
    MAX_UNCERTAINTY_COVERAGE = "maximizar_cobertura_inciertos"
    MIN_COST = "minimizar_costo"


class GameConfig(BaseModel):
    """Rules for one quiniela game."""

    game_type: GameType
    name: str
    n_matches: int = Field(gt=0)
    options: tuple[str, ...]
    cost_per_combination: float = Field(gt=0)
    min_matches: int | None = None
    max_doubles: int | None = None
    max_triples: int | None = None

    @field_validator("options")
    @classmethod
    def validate_options(cls, options: tuple[str, ...]) -> tuple[str, ...]:
        if len(options) < 2:
            raise ValueError("A game needs at least two possible outcomes.")
        if len(set(options)) != len(options):
            raise ValueError("Game outcomes must be unique.")
        return options

    @property
    def middle_option(self) -> str:
        """Return empate/diferencia option for 3-way games."""

        if len(self.options) != 3:
            raise ValueError("Only 3-way games have a middle option.")
        return self.options[1]

    def count_combinations(self, selections: list[list[str]]) -> int:
        """Return total combinations represented by a ticket."""

        self.validate_ticket(selections)
        return int(reduce(mul, (len(item) for item in selections), 1))

    def calculate_cost(self, selections: list[list[str]]) -> float:
        """Return ticket cost."""

        return self.count_combinations(selections) * self.cost_per_combination

    def validate_ticket(self, selections: list[list[str]]) -> None:
        """Validate ticket shape and allowed options."""

        if len(selections) != self.n_matches:
            raise ValueError(f"{self.name} requires {self.n_matches} matches.")
        allowed = set(self.options)
        for idx, item in enumerate(selections, start=1):
            if not item:
                raise ValueError(f"Match {idx} has no selection.")
            if len(item) > len(self.options):
                raise ValueError(f"Match {idx} has too many selections.")
            unknown = set(item) - allowed
            if unknown:
                raise ValueError(f"Match {idx} has invalid outcomes: {unknown}.")


GAME_CONFIGS: dict[GameType, GameConfig] = {
    GameType.PROGOL: GameConfig(
        game_type=GameType.PROGOL,
        name="Progol",
        n_matches=14,
        options=("L", "E", "V"),
        cost_per_combination=15.0,
        max_doubles=14,
        max_triples=5,
    ),
    GameType.PROGOL_REVANCHA: GameConfig(
        game_type=GameType.PROGOL_REVANCHA,
        name="Progol Revancha",
        n_matches=7,
        options=("L", "E", "V"),
        cost_per_combination=5.0,
        max_doubles=7,
        max_triples=3,
    ),
    GameType.PROGOL_MEDIA_SEMANA: GameConfig(
        game_type=GameType.PROGOL_MEDIA_SEMANA,
        name="Progol Media Semana",
        n_matches=9,
        options=("L", "E", "V"),
        cost_per_combination=10.0,
        max_doubles=9,
        max_triples=4,
    ),
    GameType.PROTOUCH: GameConfig(
        game_type=GameType.PROTOUCH,
        name="Protouch",
        n_matches=13,
        options=("L", "D", "V"),
        cost_per_combination=10.0,
        max_doubles=13,
        max_triples=4,
    ),
}


def get_game_config(game_type: GameType | str, n_matches: int | None = None) -> GameConfig:
    """Return a copy of the requested game config, optionally overriding matches."""

    game = GameType(game_type)
    config = GAME_CONFIGS[game].model_copy()
    if n_matches is not None:
        config.n_matches = n_matches
    return config


def format_outcome(game_type: GameType | str, outcome: str) -> str:
    """Human-readable outcome label."""

    game = GameType(game_type)
    labels = {
        "L": "Local",
        "V": "Visita",
        "E": "Empate",
        "D": "Diferencia <= 6",
    }
    if game == GameType.PROTOUCH and outcome == "D":
        return "Diferencia <= 6"
    return labels.get(outcome, outcome)

