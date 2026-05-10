from src.config.games import GameType, get_game_config


def test_progol_cost_with_doubles_and_triples():
    config = get_game_config(GameType.PROGOL)
    selections = [["L"] for _ in range(14)]
    selections[0] = ["L", "E"]
    selections[1] = ["L", "E", "V"]

    assert config.count_combinations(selections) == 6
    assert config.calculate_cost(selections) == 90


def test_protouch_options():
    config = get_game_config(GameType.PROTOUCH)

    assert config.options == ("L", "D", "V")
    assert config.n_matches == 13

