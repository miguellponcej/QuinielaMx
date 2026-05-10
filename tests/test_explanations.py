import pandas as pd

from src.config.games import GameType
from src.prediction.explanations import build_executive_explanation
from src.prediction.predictor import QuinielaPredictor
from tests.helpers import sample_trace


def test_executive_explanation_has_required_sections():
    explanation = build_executive_explanation(
        game_type=GameType.PROGOL,
        local="America",
        visitante="Guadalajara",
        probabilities={"L": 0.52, "E": 0.27, "V": 0.21},
        recommendation="L",
        coverage=["L", "E"],
        has_market=True,
    )

    assert set(explanation.lectura_rapida) == {
        "favorito",
        "riesgo",
        "recomendacion",
        "cobertura_sugerida",
    }
    assert set(explanation.factores) == {
        "localia",
        "forma_reciente",
        "diferencial_ofensivo_defensivo",
        "historial_entre_equipos",
        "mercado",
        "volatilidad",
    }
    assert explanation.recomendacion_final == "Doble"
    assert "se recomienda cubrir con doble" in explanation.mensaje


def test_prediction_dataframe_includes_executive_columns():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.read_csv("data/examples/progol_market_probs.csv")
    predictions = QuinielaPredictor(GameType.PROGOL).predict(
        df,
        market_probs=market,
        trace=sample_trace(),
    )
    frame = QuinielaPredictor(GameType.PROGOL).to_dataframe(predictions)

    expected_cols = {
        "lectura_favorito",
        "lectura_riesgo",
        "lectura_recomendacion",
        "lectura_cobertura_sugerida",
        "factor_mercado",
        "mensaje_ejecutivo",
    }
    assert expected_cols.issubset(frame.columns)
    assert frame["mensaje_ejecutivo"].str.len().min() > 0
    assert frame["factor_mercado"].str.contains("mercado", case=False).any()
