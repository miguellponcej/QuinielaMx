"""Service for loading active draws with cache, validation and recommendations."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.active_draws.draw_cache import (
    cache_age_hours,
    is_cache_fresh,
    load_active_draws_cache,
    save_active_draws_cache,
)
from src.active_draws.draw_recommendation_engine import generate_home_recommendation
from src.active_draws.draw_scheduler import active_draws_refresh_minutes
from src.active_draws.draw_validator import apply_validation
from src.active_draws.official_sources_client import OfficialSourcesClient


ACTIVE_DRAWS_LOG_DIR = Path("data/active_draws/logs")


def get_active_draws(
    force_refresh: bool = False,
    client: OfficialSourcesClient | None = None,
    user_email: str = "unknown",
) -> dict:
    """Get active draws from web or cache and attach recommendations."""

    started = time.perf_counter()
    refresh_minutes = active_draws_refresh_minutes()
    client = client or OfficialSourcesClient()
    used_cache = False
    errors: list[str] = []
    sources: list[str] = []
    payload = None
    if not force_refresh and is_cache_fresh(refresh_minutes):
        payload = load_active_draws_cache()
        used_cache = True
        if payload and _cache_needs_structured_fixture_refresh(payload):
            payload = None
            used_cache = False
    if payload is None:
        result = client.fetch_official_active_draws()
        errors.extend(result.errors)
        sources.extend(result.sources)
        if result.draws:
            if result.ok:
                save_active_draws_cache(result.draws)
            payload = {"saved_at": datetime.now(timezone.utc).isoformat(), "draws": result.draws}
        else:
            cached = load_active_draws_cache()
            if cached:
                payload = cached
                used_cache = True
            else:
                payload = {"saved_at": datetime.now(timezone.utc).isoformat(), "draws": result.draws}
    draws = [_prepare_draw(draw, used_cache) for draw in payload.get("draws", [])]
    probe = []
    if (force_refresh or not used_cache) and hasattr(client, "probe_trusted_sources"):
        probe = client.probe_trusted_sources()
    response = {
        "updated_at": payload.get("saved_at"),
        "used_cache": used_cache,
        "cache_age_hours": cache_age_hours(),
        "sources": sources,
        "source_diagnostics": probe,
        "errors": errors,
        "draws": draws,
        "summary": summarize_active_draws(draws),
        "response_seconds": round(time.perf_counter() - started, 3),
    }
    log_active_draws_update(response, user_email)
    return response


def _prepare_draw(draw: dict, used_cache: bool) -> dict:
    prepared = {**draw}
    if used_cache:
        prepared["raw_source"] = f"cache:{prepared.get('raw_source', '')}"
        prepared["data_freshness"] = "antigua" if (cache_age_hours() or 0) > 24 else "aceptable"
    prepared = apply_validation(prepared)
    prepared["recommendation"] = generate_home_recommendation(prepared)
    return prepared


def _cache_needs_structured_fixture_refresh(payload: dict) -> bool:
    """Refresh old cache entries that predate structured fixture fallback."""

    sports_draws = [draw for draw in payload.get("draws", []) if draw.get("game_type") == "sports_pool"]
    if not sports_draws:
        return False
    return all(not draw.get("matches") for draw in sports_draws)


def summarize_active_draws(draws: list[dict]) -> dict:
    """Build Home executive summary."""

    sports = [draw for draw in draws if draw.get("game_type") == "sports_pool"]
    randoms = [draw for draw in draws if draw.get("game_type") == "random_lottery"]
    recommended = [draw for draw in draws if draw.get("recommendation", {}).get("recommendation") == "Recomendado"]
    incomplete = [draw for draw in draws if draw.get("missing_fields")]
    closing_dates = [
        parsed
        for parsed in (_parse_datetime(draw.get("closing_date")) for draw in draws)
        if parsed is not None
    ]
    return {
        "total_games": len(draws),
        "sports_pools": len(sports),
        "random_lotteries": len(randoms),
        "recommended_games": len(recommended),
        "incomplete_games": len(incomplete),
        "next_closing": min(closing_dates).isoformat() if closing_dates else "Dato no disponible",
    }


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


def log_active_draws_update(response: dict, user_email: str = "unknown") -> Path:
    """Save update log in data/active_draws/logs."""

    ACTIVE_DRAWS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = ACTIVE_DRAWS_LOG_DIR / f"active_draws_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user_email,
        "sources": response.get("sources", []),
        "games_found": [draw.get("game_name") for draw in response.get("draws", [])],
        "missing_data": {draw.get("game_name"): draw.get("missing_fields", []) for draw in response.get("draws", [])},
        "errors": response.get("errors", []),
        "used_cache": response.get("used_cache"),
        "response_seconds": response.get("response_seconds"),
        "recommendations": {
            draw.get("game_name"): draw.get("recommendation", {}).get("recommendation")
            for draw in response.get("draws", [])
        },
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return path
