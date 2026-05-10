"""Home recommendation and decision-center helpers."""

from __future__ import annotations

from datetime import datetime, timezone


SPORTS_POOL_TYPES = {"progol", "progol_revancha", "progol_media_semana", "protouch"}


def build_decision_rows(draws: list[dict]) -> list[dict]:
    """Build the executive Home table rows."""

    rows = []
    for position, draw in enumerate(sort_recommendations(draws), start=1):
        rec = draw.get("recommendation", {})
        rows.append(
            {
                "prioridad": position,
                "juego": draw.get("game_name", "Dato no disponible"),
                "tipo": _display_game_type(draw.get("game_type")),
                "estado": draw.get("status", "Dato no disponible"),
                "cierre": draw.get("closing_date", "Dato no disponible"),
                "calidad_datos": draw.get("data_quality_score", 0),
                "recomendacion": rec.get("recommendation", "Dato no disponible"),
                "score": rec.get("recommendation_score", 0),
                "accion_sugerida": recommended_action(draw),
                "prediccion_directa": "Si" if can_generate_prediction(draw) else "No",
                "requiere_fuente_web": "Si" if requires_manual_load(draw) else "No",
            }
        )
    return rows


def sort_recommendations(draws: list[dict]) -> list[dict]:
    """Sort draws by decision priority for the Home dashboard."""

    return sorted(draws, key=decision_priority, reverse=True)


def decision_priority(draw: dict) -> float:
    """Return a ranking score focused on what the user should do next."""

    rec = draw.get("recommendation", {})
    score = float(rec.get("recommendation_score", 0) or 0)
    quality = float(draw.get("data_quality_score", 0) or 0)
    priority = score * 0.55 + quality * 0.30
    if can_generate_prediction(draw):
        priority += 18
    if requires_manual_load(draw):
        priority -= 10
    if draw.get("recommendation", {}).get("recommendation") == "No prioritario":
        priority -= 12
    priority += _closing_urgency_bonus(draw.get("closing_date"))
    return priority


def can_generate_prediction(draw: dict) -> bool:
    """Return whether Home can launch a sports prediction immediately."""

    if draw.get("game_type") != "sports_pool":
        return False
    if not draw.get("matches"):
        return False
    if draw.get("status") not in {"active", "Vigente", "Dato no disponible"}:
        return False
    return draw.get("recommendation", {}).get("recommendation") != "No prioritario"


def requires_manual_load(draw: dict) -> bool:
    """Return whether the draw needs more web data to become actionable."""

    if draw.get("missing_fields") or draw.get("source_errors"):
        return True
    if draw.get("game_type") == "sports_pool" and not draw.get("matches"):
        return True
    return False


def recommended_action(draw: dict) -> str:
    """Human action label for Home."""

    if can_generate_prediction(draw):
        return "Generar prediccion"
    if requires_manual_load(draw):
        return "Actualizar fuentes web"
    if draw.get("game_type") == "random_lottery":
        return "Ver analisis informativo"
    return draw.get("recommendation", {}).get("recommended_action", "Revisar despues")


def ready_for_prediction(draws: list[dict]) -> list[dict]:
    """Return sports draws with structured matches available."""

    return [draw for draw in sort_recommendations(draws) if can_generate_prediction(draw)]


def manual_load_required(draws: list[dict]) -> list[dict]:
    """Return draws that need more web data before prediction."""

    return [draw for draw in sort_recommendations(draws) if requires_manual_load(draw)]


def best_quality_draws(draws: list[dict], limit: int = 3) -> list[dict]:
    """Return draws with the strongest data quality."""

    return sorted(draws, key=lambda draw: draw.get("data_quality_score", 0), reverse=True)[:limit]


def next_closing_draw(draws: list[dict]) -> dict | None:
    """Return the draw with the nearest known future closing date."""

    dated = []
    for draw in draws:
        closing = _parse_datetime(draw.get("closing_date"))
        if closing is not None:
            dated.append((closing, draw))
    if not dated:
        return None
    return min(dated, key=lambda item: item[0])[1]


def _closing_sort_value(value: object) -> int:
    if value in (None, "", "Dato no disponible"):
        return 0
    return 1


def _closing_urgency_bonus(value: object) -> float:
    closing = _parse_datetime(value)
    if closing is None:
        return 0
    now = datetime.now(timezone.utc)
    hours = (closing - now).total_seconds() / 3600
    if hours < 0:
        return -15
    if hours <= 24:
        return 10
    if hours <= 72:
        return 6
    return 2


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, "", "Dato no disponible"):
        return None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _display_game_type(value: object) -> str:
    return {
        "sports_pool": "Quiniela deportiva",
        "random_lottery": "Sorteo aleatorio",
        "special_draw": "Sorteo especial",
    }.get(str(value), "Dato no disponible")
