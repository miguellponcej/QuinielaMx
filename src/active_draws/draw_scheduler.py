"""Refresh interval helpers for active draws."""

from __future__ import annotations

from src.security.secrets import get_env


def active_draws_refresh_minutes() -> int:
    """Return configured active draws refresh interval."""

    return int(get_env("ACTIVE_DRAWS_REFRESH_MINUTES", "60"))

