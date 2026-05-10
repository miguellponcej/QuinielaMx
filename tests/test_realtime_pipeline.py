import pandas as pd
import pytest

from src.config.games import GameType
from src.realtime.real_time_prediction_pipeline import real_time_prediction_pipeline
from tests.helpers import sample_trace


def test_realtime_pipeline_generates_prediction_and_ticket():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.read_csv("data/examples/progol_market_probs.csv")

    result = real_time_prediction_pipeline(
        GameType.PROGOL,
        df,
        trace=sample_trace(),
        market_probs=market,
        budget=300,
    )

    assert len(result.predictions) == 14
    assert result.ticket is not None
    assert result.ticket.cost <= 300
    assert "archivos_usados" in result.prediction_frame.columns
    assert "momios" in result.prediction_frame.columns
    assert "fuente_momio" in result.prediction_frame.columns


def test_realtime_pipeline_surfaces_market_odds_and_source():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.DataFrame(
        [
            {
                "id": idx,
                "momio_l": 1.9,
                "momio_e": 3.2,
                "momio_v": 4.0,
                "fuente_momio": "Caliente prueba",
            }
            for idx in range(1, 15)
        ]
    )

    result = real_time_prediction_pipeline(
        GameType.PROGOL,
        df,
        trace=sample_trace(),
        market_probs=market,
        budget=300,
    )

    first = result.prediction_frame.iloc[0]
    assert first["momio_l"] == 1.9
    assert first["fuente_momio"] == "Caliente prueba"
    assert first["mercado_disponible"] == "Si"


def test_realtime_pipeline_extracts_embedded_web_odds():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    df["odds_l"] = 1.8
    df["odds_e"] = 3.4
    df["odds_v"] = 4.2
    df["bookmaker"] = "The Odds API prueba"

    result = real_time_prediction_pipeline(GameType.PROGOL, df, trace=sample_trace(), budget=300)

    first = result.prediction_frame.iloc[0]
    assert first["momio_l"] == 1.8
    assert first["fuente_momio"] == "The Odds API prueba"


def test_realtime_pipeline_rejects_missing_match_columns():
    df = pd.DataFrame([{"id": 1, "local": "A"}])

    with pytest.raises(ValueError, match="Faltan columnas"):
        real_time_prediction_pipeline(GameType.PROGOL, df, trace=sample_trace(), n_matches=1)
