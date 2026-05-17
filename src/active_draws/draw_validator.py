"""Validation for active draw records."""

from __future__ import annotations

from datetime import datetime, time, timezone

from src.active_draws.draw_parser import NOT_AVAILABLE


REQUIRED_FIELDS = ["game_id", "game_name", "game_type", "official_url", "last_updated"]


def validate_active_draw(draw: dict) -> dict:
    """Validate one active draw and calculate quality score."""

    warnings: list[str] = []
    missing_fields = [field for field in REQUIRED_FIELDS if not draw.get(field)]
    important = ["closing_date", "draw_date", "estimated_prize", "accumulated_pool", "cost_per_entry"]
    missing_fields.extend(field for field in important if _missing(draw.get(field)))
    if _missing(draw.get("game_name")):
        warnings.append("El juego no tiene nombre.")
    if not draw.get("last_updated"):
        warnings.append("La fuente no tiene fecha de consulta.")
    for money_field in ["cost_per_entry", "estimated_prize", "accumulated_pool"]:
        value = draw.get(money_field)
        if not _missing(value) and not _is_number_like(value):
            warnings.append(f"{money_field} no es numerico.")
    if draw.get("game_type") == "sports_pool":
        matches = draw.get("matches") or []
        if not matches:
            warnings.append("No hay partidos deportivos estructurados.")
        for match in matches:
            if not match.get("local") or not match.get("visitante"):
                warnings.append("Hay partidos sin local o visitante.")
    if _is_expired(draw.get("closing_date")):
        warnings.append("La fecha limite parece vencida.")
    if draw.get("game_type") == "sports_pool" and not _has_future_or_today_match(draw) and _is_expired(draw.get("draw_date")):
        warnings.append("La fecha de celebracion ya paso.")
    score = _score(draw, missing_fields, warnings)
    return {
        "is_valid": bool(draw.get("game_name")) and bool(draw.get("official_url")),
        "warnings": sorted(set(warnings)),
        "missing_fields": sorted(set(missing_fields)),
        "data_quality_score": score,
    }


def apply_validation(draw: dict) -> dict:
    """Attach validation output to a draw."""

    validation = validate_active_draw(draw)
    draw = {**draw}
    if _is_expired(draw.get("closing_date")):
        draw["status"] = "closed"
    if draw.get("game_type") == "sports_pool" and not _has_future_or_today_match(draw) and _is_expired(draw.get("draw_date")):
        draw["status"] = "closed"
    draw["validation"] = validation
    draw["missing_fields"] = validation["missing_fields"]
    draw["data_quality_score"] = validation["data_quality_score"]
    return draw


def _missing(value: object) -> bool:
    return value in (None, "", NOT_AVAILABLE)


def _is_number_like(value: object) -> bool:
    try:
        float(str(value).replace(",", "").replace("$", ""))
        return True
    except ValueError:
        return False


def _is_expired(value: object) -> bool:
    if _missing(value):
        return False
    parsed = _parse_datetime(value)
    if parsed is None:
        return False
    return parsed < datetime.now(parsed.tzinfo or timezone.utc)


def _has_future_or_today_match(draw: dict) -> bool:
    today = datetime.now(timezone.utc).date()
    for match in draw.get("matches") or []:
        parsed = _parse_datetime(match.get("fecha"))
        if parsed and parsed.date() >= today:
            return True
    return False


def _parse_datetime(value: object) -> datetime | None:
    if _missing(value):
        return None
    text = str(value).strip()
    candidates = [text]
    if text.endswith("Z"):
        candidates.append(text.replace("Z", "+00:00"))
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            date_value = datetime.strptime(text, fmt).date()
            return datetime.combine(date_value, time.max, tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _score(draw: dict, missing_fields: list[str], warnings: list[str]) -> int:
    score = 100
    score -= min(60, len(set(missing_fields)) * 8)
    score -= min(30, len(set(warnings)) * 10)
    if draw.get("data_freshness") == "actualizada":
        score += 5
    if draw.get("raw_source", "").startswith("cache"):
        score -= 15
    return max(0, min(100, score))
