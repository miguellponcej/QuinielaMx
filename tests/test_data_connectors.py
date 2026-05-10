import pandas as pd
import pytest

from src.config.games import GameType, get_game_config
from src.data.connectors import LocalDataConnector
from src.data.validators import validate_market_probabilities, validate_ticket_budget


def test_load_soccer_results_from_csv():
    result = LocalDataConnector().load_soccer_results("data/examples/match_results_soccer.csv")

    assert not result.frame.empty
    assert {"local_key", "visitante_key"}.issubset(result.frame.columns)


def test_load_current_quiniela_validates_match_count():
    config = get_game_config(GameType.PROGOL)
    result = LocalDataConnector().load_current_quiniela("data/examples/progol_quiniela.csv", config)

    assert len(result.frame) == 14


def test_market_probabilities_must_sum_to_one():
    config = get_game_config(GameType.PROGOL)
    bad = pd.DataFrame({"id": range(1, 15), "prob_l": 0.5, "prob_e": 0.5, "prob_v": 0.5})

    with pytest.raises(ValueError):
        validate_market_probabilities(bad, config)


def test_ticket_budget_validation_rejects_unaffordable_ticket():
    config = get_game_config(GameType.PROGOL)
    selections = [["L", "E"] for _ in range(14)]

    with pytest.raises(ValueError):
        validate_ticket_budget(config, selections, budget=100)

