"""Private JSONL storage for prediction history and evaluations."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_DIR_NAME = "prediction_history"
PREDICTIONS_FILE = "predictions.jsonl"
OFFICIAL_RESULTS_FILE = "official_results.jsonl"
EVALUATIONS_FILE = "evaluations.jsonl"


@dataclass(frozen=True)
class PredictionHistoryRecord:
    """One immutable prediction run saved for audit and learning."""

    run_id: str
    game_id: str
    game_name: str
    draw_number: str
    draw_date: str
    created_at: str
    model_version: str
    source_urls: list[str]
    data_quality_notes: list[str]
    predictions: list[dict[str, Any]]
    ticket: dict[str, Any] | None = None
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OfficialResultsRecord:
    """Official result record for one contest."""

    result_id: str
    game_id: str
    draw_number: str
    draw_date: str
    source_url: str
    recorded_at: str
    results: list[dict[str, Any]]


@dataclass(frozen=True)
class EvaluationRecord:
    """Comparison between saved predictions and official results."""

    evaluation_id: str
    run_id: str
    result_id: str
    game_id: str
    draw_number: str
    evaluated_at: str
    total_matches: int
    direct_hits: int
    coverage_hits: int
    accuracy: float
    coverage_accuracy: float
    brier_score: float | None
    match_rows: list[dict[str, Any]]


def history_dir(base_dir: str | Path | None = None) -> Path:
    """Return private history directory."""

    root = Path(base_dir or os.getenv("DATA_DIR", "data"))
    return root / HISTORY_DIR_NAME


def record_prediction_run(
    result: Any,
    game_id: str,
    draw: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PredictionHistoryRecord:
    """Persist one prediction run as append-only JSONL."""

    draw = draw or {}
    created_at = datetime.now(timezone.utc).isoformat()
    draw_number = _clean(draw.get("draw_number"))
    draw_date = _clean(draw.get("draw_date"))
    run_id = _stable_id([game_id, draw_number, created_at])
    predictions = [prediction.as_dict() for prediction in result.predictions]
    ticket = _ticket_to_dict(result.ticket)
    source_urls = list(
        dict.fromkeys(
            [
                *[source.location for source in result.trace.web_sources],
                *([str(draw.get("official_url"))] if draw.get("official_url") not in (None, "", "Dato no disponible") else []),
                *[str(source) for source in draw.get("alternate_sources", []) or []],
            ]
        )
    )
    record = PredictionHistoryRecord(
        run_id=run_id,
        game_id=game_id,
        game_name=result.game_config.name,
        draw_number=draw_number,
        draw_date=draw_date,
        created_at=created_at,
        model_version=result.trace.model_version,
        source_urls=source_urls,
        data_quality_notes=result.data_quality_notes,
        predictions=predictions,
        ticket=ticket,
        trace=result.trace.as_dict(),
    )
    _append_jsonl(_path(PREDICTIONS_FILE, base_dir), asdict(record))
    return record


def record_official_results(
    game_id: str,
    draw_number: str,
    results: list[dict[str, Any]],
    draw_date: str = "Dato no disponible",
    source_url: str = "Dato no disponible",
    base_dir: str | Path | None = None,
) -> OfficialResultsRecord:
    """Persist official contest results for later comparison."""

    recorded_at = datetime.now(timezone.utc).isoformat()
    result_id = _stable_id([game_id, draw_number, source_url])
    normalized = [_normalize_result_row(row) for row in results]
    record = OfficialResultsRecord(
        result_id=result_id,
        game_id=game_id,
        draw_number=_clean(draw_number),
        draw_date=_clean(draw_date),
        source_url=_clean(source_url),
        recorded_at=recorded_at,
        results=normalized,
    )
    _append_unique_jsonl(_path(OFFICIAL_RESULTS_FILE, base_dir), asdict(record), "result_id")
    return record


def load_prediction_history(base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Load saved prediction runs."""

    return _read_jsonl(_path(PREDICTIONS_FILE, base_dir))


def load_official_results_history(base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Load saved official results."""

    return _read_jsonl(_path(OFFICIAL_RESULTS_FILE, base_dir))


def load_evaluation_history(base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Load saved prediction evaluations."""

    return _read_jsonl(_path(EVALUATIONS_FILE, base_dir))


def _path(file_name: str, base_dir: str | Path | None = None) -> Path:
    return history_dir(base_dir) / file_name


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, default=str) + "\n")


def _append_unique_jsonl(path: Path, payload: dict[str, Any], key: str) -> None:
    existing = {item.get(key) for item in _read_jsonl(path)}
    if payload.get(key) in existing:
        return
    _append_jsonl(path, payload)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _ticket_to_dict(ticket: Any | None) -> dict[str, Any] | None:
    if ticket is None:
        return None
    return {
        "combinations": ticket.combinations,
        "cost": ticket.cost,
        "probability_all_correct": ticket.probability_all_correct,
        "selections": ticket.selections,
        "table": ticket.table.to_dict(orient="records"),
    }


def _normalize_result_row(row: dict[str, Any]) -> dict[str, Any]:
    match_id = row.get("id", row.get("partido", row.get("match_id")))
    actual = row.get("resultado", row.get("actual_result", row.get("oficial")))
    return {
        "id": int(match_id),
        "actual_result": str(actual).strip().upper(),
        "source_note": str(row.get("source_note", "")),
    }


def _clean(value: Any) -> str:
    if value in (None, ""):
        return "Dato no disponible"
    return str(value)


def _stable_id(parts: list[Any]) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
