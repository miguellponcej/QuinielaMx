from src.models.nfl_model import NFLMarginModel
from src.models.poisson_soccer import PoissonSoccerModel


def test_poisson_probabilities_sum_to_one():
    model = PoissonSoccerModel()
    probs = model.predict("America", "Pumas")

    assert set(probs) == {"L", "E", "V"}
    assert abs(sum(probs.values()) - 1) < 1e-9


def test_nfl_margin_probabilities_sum_to_one():
    model = NFLMarginModel()
    probs = model.predict_from_spread(3.5)

    assert set(probs) == {"L", "D", "V"}
    assert abs(sum(probs.values()) - 1) < 1e-9

