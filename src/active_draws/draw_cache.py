"""Active draws cache management."""

from __future__ import annotations

import json
from json import JSONDecodeError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CACHE_DIR = Path("data/active_draws/cache")
CACHE_FILE = CACHE_DIR / "active_draws_cache.json"


def save_active_draws_cache(draws: list[dict], cache_path: str | Path = CACHE_FILE) -> Path:
    """Save active draws cache."""

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": datetime.now(timezone.utc).isoformat(), "draws": draws}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


def load_active_draws_cache(cache_path: str | Path = CACHE_FILE) -> dict[str, Any] | None:
    """Load active draws cache."""

    path = Path(cache_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (JSONDecodeError, OSError, TypeError):
        return None
    if not isinstance(payload, dict) or "draws" not in payload or "saved_at" not in payload:
        return None
    return payload


def is_cache_fresh(max_age_minutes: int = 60, cache_path: str | Path = CACHE_FILE) -> bool:
    """Return whether the cache is fresh enough."""

    payload = load_active_draws_cache(cache_path)
    if not payload:
        return False
    try:
        saved_at = datetime.fromisoformat(payload["saved_at"])
    except (ValueError, TypeError):
        return False
    return datetime.now(timezone.utc) - saved_at <= timedelta(minutes=max_age_minutes)


def cache_age_hours(cache_path: str | Path = CACHE_FILE) -> float | None:
    """Return cache age in hours."""

    payload = load_active_draws_cache(cache_path)
    if not payload:
        return None
    try:
        saved_at = datetime.fromisoformat(payload["saved_at"])
    except (ValueError, TypeError):
        return None
    return (datetime.now(timezone.utc) - saved_at).total_seconds() / 3600
