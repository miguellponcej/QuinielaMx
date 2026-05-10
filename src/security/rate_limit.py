"""Simple in-memory rate limiting for login attempts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class RateLimiter:
    """Block repeated failed login attempts temporarily."""

    max_attempts: int = 5
    window_seconds: int = 900
    block_seconds: int = 900
    attempts: dict[str, list[datetime]] = field(default_factory=dict)
    blocked_until: dict[str, datetime] = field(default_factory=dict)

    def is_blocked(self, key: str) -> bool:
        """Return whether a key is temporarily blocked."""

        now = datetime.now(timezone.utc)
        until = self.blocked_until.get(key)
        if until is None:
            return False
        if now >= until:
            self.blocked_until.pop(key, None)
            return False
        return True

    def register_failure(self, key: str) -> None:
        """Register a failed attempt and block if needed."""

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        recent = [item for item in self.attempts.get(key, []) if item >= cutoff]
        recent.append(now)
        self.attempts[key] = recent
        if len(recent) >= self.max_attempts:
            self.blocked_until[key] = now + timedelta(seconds=self.block_seconds)

    def register_success(self, key: str) -> None:
        """Clear failures after successful login."""

        self.attempts.pop(key, None)
        self.blocked_until.pop(key, None)

