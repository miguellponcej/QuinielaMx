import pandas as pd

from src.config.games import GameType
from src.history.evaluator import evaluate_prediction_run, summarize_model_performance
from src.history.storage import (
    load_evaluation_history,
    load_official_results_history,
    load_prediction_history,
    record_official_results,
    record_prediction_run,
)
from src.realtime.real_time_prediction_pipeline import real_time_prediction_pipeline
from tests.helpers import sample_trace


def test_prediction_history_and_official_evaluation(tmp_path):
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    result = real_time_prediction_pipeline(GameType.PROGOL, df, trace=sample_trace(), budget=300)
    record = record_prediction_run(
        result,
        game_id="progol",
        draw={"draw_number": "999", "draw_date": "2099-01-01", "official_url": "https://pronosticos.gob.mx/Progol/Quiniela"},
        base_dir=tmp_path,
    )
    official = record_official_results(
        "progol",
        "999",
        [{"id": idx, "actual_result": "L"} for idx in range(1, 15)],
        source_url="https://www.loterianacional.gob.mx/Home/Resultados",
        base_dir=tmp_path,
    )

    evaluation = evaluate_prediction_run(record.run_id, result_id=official.result_id, base_dir=tmp_path)
    summary = summarize_model_performance(base_dir=tmp_path)

    assert len(load_prediction_history(tmp_path)) == 1
    assert len(load_official_results_history(tmp_path)) == 1
    assert len(load_evaluation_history(tmp_path)) == 1
    assert evaluation.total_matches == 14
    assert 0 <= evaluation.accuracy <= 1
    assert summary["matches"] == 14
