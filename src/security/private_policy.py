"""Private-by-default security policy."""

from __future__ import annotations

from src.security.secrets import get_bool_env


def private_by_default_enabled() -> bool:
    """Return whether private-by-default mode is enabled."""

    return get_bool_env("PRIVATE_BY_DEFAULT", True)


def assert_private_by_default() -> None:
    """Raise if private-by-default policy is disabled."""

    if not private_by_default_enabled():
        raise RuntimeError("PRIVATE_BY_DEFAULT cannot be disabled for this application.")

