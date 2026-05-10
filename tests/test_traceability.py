import pandas as pd
import pytest

from src.audit.provenance import TraceValidationError, build_manual_trace
from src.config.games import GameType
from src.prediction.predictor import QuinielaPredictor
from tests.helpers import sample_trace


def test_prediction_requires_traceability_context():
    df = pd.read_csv("data/examples/progol_quiniela.csv")

    with pytest.raises(TraceValidationError):
        QuinielaPredictor(GameType.PROGOL).predict(df)


def test_trace_summary_is_in_prediction_output():
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.read_csv("data/examples/progol_market_probs.csv")
    predictor = QuinielaPredictor(GameType.PROGOL)

    frame = predictor.to_dataframe(predictor.predict(df, market_probs=market, trace=sample_trace()))

    assert "archivos_usados" in frame.columns
    assert "fuentes_web_consultadas" in frame.columns
    assert "variables_modelo" in frame.columns
    assert "version_modelo" in frame.columns


def test_trace_validation_rejects_missing_web_sources():
    trace = build_manual_trace(
        internal_file_paths=["data/examples/progol_quiniela.csv"],
        web_locations=[],
        model_variables=["probabilidades"],
    )

    with pytest.raises(TraceValidationError):
        trace.validate_ready()

