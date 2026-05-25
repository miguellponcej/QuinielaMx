"""Conservative learning from historical prediction evaluations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.history.storage import load_evaluation_history
from src.prediction.predictor import MatchPrediction
from src.utils.probability import normalize_probabilities


def build_learning_context(
    game_id: str,
    base_dir: str | Path | None = None,
    min_matches: int = 30,
) -> dict[str, Any]:
    """Return historical calibration context for one game.

    The context is intentionally conservative. It only becomes active when
    enough official-result comparisons exist.
    """

    evaluations = [item for item in load_evaluation_history(base_dir) if item.get("game_id") == game_id]
    rows = [row for evaluation in evaluations for row in evaluation.get("match_rows", [])]
    if len(rows) < min_matches:
        return {
            "active": False,
            "sample_size": len(rows),
            "message": "Historial insuficiente para recalibrar sin sobreajustar.",
            "accuracy_by_pick": {},
        }
    grouped: dict[str, list[bool]] = {}
    for row in rows:
        pick = str(row.get("prediccion", "")).upper()
        if not pick:
            continue
        grouped.setdefault(pick, []).append(bool(row.get("direct_hit")))
    accuracy_by_pick = {
        pick: sum(values) / len(values)
        for pick, values in grouped.items()
        if len(values) >= max(5, min_matches // 6)
    }
    return {
        "active": bool(accuracy_by_pick),
        "sample_size": len(rows),
        "message": "Ajuste historico disponible." if accuracy_by_pick else "Muestra historica insuficiente por seleccion.",
        "accuracy_by_pick": accuracy_by_pick,
    }


def apply_historical_learning(
    predictions: list[MatchPrediction],
    game_id: str,
    base_dir: str | Path | None = None,
    min_matches: int = 30,
) -> dict[str, Any]:
    """Apply a small probability adjustment from historical hit rates."""

    context = build_learning_context(game_id, base_dir=base_dir, min_matches=min_matches)
    if not context["active"]:
        return context
    accuracy_by_pick = context["accuracy_by_pick"]
    for prediction in predictions:
        pick = prediction.recommendation.upper()
        historical_accuracy = accuracy_by_pick.get(pick)
        if historical_accuracy is None:
            continue
        adjusted = dict(prediction.probabilities)
        current = adjusted.get(prediction.recommendation)
        if current is None:
            continue
        target = min(0.78, max(0.18, historical_accuracy))
        adjusted[prediction.recommendation] = (current * 0.85) + (target * 0.15)
        normalized = normalize_probabilities(list(adjusted.values()))
        prediction.probabilities = dict(zip(adjusted.keys(), map(float, normalized), strict=True))
        prediction.explanation = f"{prediction.explanation} Ajuste historico aplicado con muestra previa."
        prediction.market_note = (prediction.market_note + " | " if prediction.market_note else "") + "Ajuste historico aplicado"
    return context
