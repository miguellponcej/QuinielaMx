import pandas as pd

from src.config.games import GameType, get_game_config
from src.optimization.monte_carlo import MonteCarloSimulator
from src.prediction.predictor import QuinielaPredictor
from tests.helpers import sample_trace


def test_monte_carlo_distribution():
    df = pd.read_csv("data/examples/protouch_quiniela.csv")
    market = pd.read_csv("data/examples/protouch_market_probs.csv")
    config = get_game_config(GameType.PROTOUCH)
    predictions = QuinielaPredictor(GameType.PROTOUCH).predict(
        df,
        market_probs=market,
        trace=sample_trace(),
    )
    selections = [[prediction.recommendation] for prediction in predictions]

    result = MonteCarloSimulator(config).simulate(predictions, selections, scenarios=2000)

    assert not result.summary.empty
    assert result.hits_distribution["probabilidad"].sum() == 1
