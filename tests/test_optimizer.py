import pandas as pd

from src.config.games import GameType, get_game_config
from src.optimization.low_cost_optimizer import optimize_low_cost_ticket
from src.optimization.ticket_optimizer import TicketOptimizer
from src.prediction.predictor import QuinielaPredictor
from tests.helpers import sample_trace


def _sample_predictions():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.read_csv("data/examples/progol_market_probs.csv")
    predictor = QuinielaPredictor(GameType.PROGOL)
    return predictor.predict(df, market_probs=market, trace=sample_trace())


def test_optimizer_respects_budget():
    config = get_game_config(GameType.PROGOL)
    predictions = _sample_predictions()
    optimizer = TicketOptimizer(config)

    ticket = optimizer.optimize(predictions, budget=180, max_doubles=4, max_triples=1)

    assert ticket.cost <= 180
    assert ticket.combinations >= 1


def test_low_cost_strategies_return_summary():
    config = get_game_config(GameType.PROGOL)
    predictions = _sample_predictions()

    strategies = optimize_low_cost_ticket(predictions, config, budget=500)

    assert len(strategies.resumen) == 4
    assert strategies.economica.cost <= 500


def test_economic_scenario_limits_coverage():
    config = get_game_config(GameType.PROGOL)
    predictions = _sample_predictions()

    strategies = optimize_low_cost_ticket(predictions, config, budget=1000)

    assert sum(1 for item in strategies.economico.selections if len(item) == 2) <= 3
    assert sum(1 for item in strategies.economico.selections if len(item) == 3) == 0


def test_optimizer_table_contains_coverage_reason():
    config = get_game_config(GameType.PROGOL)
    predictions = _sample_predictions()
    optimizer = TicketOptimizer(config)

    ticket = optimizer.optimize(predictions, budget=300, max_doubles=4, max_triples=1)

    expected = {
        "partido",
        "seleccion_fija",
        "cobertura_recomendada",
        "probabilidad_principal",
        "riesgo",
        "motivo_cobertura",
    }
    assert expected.issubset(ticket.table.columns)
    assert ticket.table["motivo_cobertura"].str.len().min() > 0


def test_marginal_steps_track_positive_value():
    config = get_game_config(GameType.PROGOL)
    predictions = _sample_predictions()
    optimizer = TicketOptimizer(config)

    ticket = optimizer.optimize(predictions, budget=600, max_doubles=6, max_triples=2)

    if len(ticket.marginal_steps) > 0:
        assert (ticket.marginal_steps["beneficio_probabilistico"] > 0).all()
        assert (ticket.marginal_steps["costo_marginal"] > 0).all()
        assert (ticket.marginal_steps["ratio_beneficio_costo"] > 0).all()
    assert ticket.cost <= 600
