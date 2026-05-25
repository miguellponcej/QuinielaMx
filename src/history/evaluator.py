"""Evaluate saved predictions against official contest results."""

from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.history.storage import (
    EVALUATIONS_FILE,
    EvaluationRecord,
    history_dir,
    load_evaluation_history,
    load_official_results_history,
    load_prediction_history,
)

import json


def evaluate_prediction_run(
    run_id: str | None = None,
    game_id: str | None = None,
    draw_number: str | None = None,
    result_id: str | None = None,
    base_dir: str | Path | None = None,
) -> EvaluationRecord:
    """Compare one saved prediction run against official results."""

    prediction = _find_prediction(run_id, game_id, draw_number, base_dir)
    official = _find_official_result(result_id, prediction["game_id"], prediction["draw_number"], base_dir)
    rows = _match_rows(prediction["predictions"], official["results"])
    total = len(rows)
    direct_hits = sum(1 for row in rows if row["direct_hit"])
    coverage_hits = sum(1 for row in rows if row["coverage_hit"])
    brier_values = [row["brier"] for row in rows if row["brier"] is not None]
    brier = sum(brier_values) / len(brier_values) if brier_values else None
    record = EvaluationRecord(
        evaluation_id=f"{prediction['run_id']}:{official['result_id']}",
        run_id=prediction["run_id"],
        result_id=official["result_id"],
        game_id=prediction["game_id"],
        draw_number=prediction["draw_number"],
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        total_matches=total,
        direct_hits=direct_hits,
        coverage_hits=coverage_hits,
        accuracy=direct_hits / total if total else 0.0,
        coverage_accuracy=coverage_hits / total if total else 0.0,
        brier_score=brier,
        match_rows=rows,
    )
    _append_evaluation(record, base_dir)
    return record


def summarize_model_performance(base_dir: str | Path | None = None) -> dict[str, Any]:
    """Summarize historical performance for the Historial page."""

    evaluations = load_evaluation_history(base_dir)
    if not evaluations:
        return {
            "runs": 0,
            "matches": 0,
            "accuracy": 0.0,
            "coverage_accuracy": 0.0,
            "brier_score": None,
        }
    matches = sum(int(item.get("total_matches", 0)) for item in evaluations)
    direct_hits = sum(int(item.get("direct_hits", 0)) for item in evaluations)
    coverage_hits = sum(int(item.get("coverage_hits", 0)) for item in evaluations)
    briers = [float(item["brier_score"]) for item in evaluations if item.get("brier_score") is not None]
    return {
        "runs": len(evaluations),
        "matches": matches,
        "accuracy": direct_hits / matches if matches else 0.0,
        "coverage_accuracy": coverage_hits / matches if matches else 0.0,
        "brier_score": sum(briers) / len(briers) if briers else None,
    }


def _find_prediction(
    run_id: str | None,
    game_id: str | None,
    draw_number: str | None,
    base_dir: str | Path | None,
) -> dict[str, Any]:
    predictions = load_prediction_history(base_dir)
    candidates = predictions
    if run_id:
        candidates = [item for item in candidates if item.get("run_id") == run_id]
    if game_id:
        candidates = [item for item in candidates if item.get("game_id") == game_id]
    if draw_number:
        candidates = [item for item in candidates if item.get("draw_number") == str(draw_number)]
    if not candidates:
        raise ValueError("No se encontro historial de prediccion para evaluar.")
    return sorted(candidates, key=lambda item: item.get("created_at", ""))[-1]


def _find_official_result(
    result_id: str | None,
    game_id: str,
    draw_number: str,
    base_dir: str | Path | None,
) -> dict[str, Any]:
    results = load_official_results_history(base_dir)
    candidates = results
    if result_id:
        candidates = [item for item in candidates if item.get("result_id") == result_id]
    else:
        candidates = [
            item
            for item in candidates
            if item.get("game_id") == game_id and str(item.get("draw_number")) == str(draw_number)
        ]
    if not candidates:
        raise ValueError("No se encontraron resultados oficiales guardados para comparar.")
    return sorted(candidates, key=lambda item: item.get("recorded_at", ""))[-1]


def _match_rows(predictions: list[dict[str, Any]], official_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    official_by_id = {int(row["id"]): row for row in official_results}
    rows = []
    for prediction in predictions:
        match_id = int(prediction["id"])
        official = official_by_id.get(match_id)
        if not official:
            continue
        actual = str(official["actual_result"]).upper()
        recommended = str(prediction.get("recomendacion", "")).upper()
        coverage = [item.strip().upper() for item in str(prediction.get("cobertura", "")).split("/") if item.strip()]
        probabilities = _probabilities(prediction)
        rows.append(
            {
                "id": match_id,
                "partido": f"{prediction.get('local')} vs {prediction.get('visitante')}",
                "prediccion": recommended,
                "cobertura": "/".join(coverage),
                "resultado_oficial": actual,
                "direct_hit": recommended == actual,
                "coverage_hit": actual in coverage,
                "brier": _brier(actual, probabilities),
            }
        )
    return rows


def _probabilities(prediction: dict[str, Any]) -> dict[str, float]:
    values = {}
    for key, value in prediction.items():
        if str(key).startswith("prob_"):
            values[str(key).replace("prob_", "").upper()] = float(value)
    return values


def _brier(actual: str, probabilities: dict[str, float]) -> float | None:
    if not probabilities:
        return None
    labels = sorted(probabilities)
    if actual not in labels:
        return None
    return float(sum((probabilities[label] - (1.0 if label == actual else 0.0)) ** 2 for label in labels) / len(labels))


def _append_evaluation(record: EvaluationRecord, base_dir: str | Path | None) -> None:
    path = history_dir(base_dir) / EVALUATIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {item.get("evaluation_id") for item in load_evaluation_history(base_dir)}
    if record.evaluation_id in existing:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=True, default=str) + "\n")
