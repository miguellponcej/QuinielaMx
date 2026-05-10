"""Session helpers for Streamlit-compatible state mappings."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


SESSION_KEY = "auth_session"


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user identity."""

    name: str
    email: str
    login_at: str
    last_access_at: str


class SessionManager:
    """Create, validate and destroy auth sessions."""

    def __init__(self, state: MutableMapping[str, Any], ttl_seconds: int = 28800) -> None:
        self.state = state
        self.ttl_seconds = ttl_seconds

    def create_session(self, email: str, name: str = "") -> AuthUser:
        """Create a new session."""

        now = datetime.now(timezone.utc)
        user = AuthUser(
            name=name or email.split("@")[0],
            email=email.lower(),
            login_at=now.isoformat(),
            last_access_at=now.isoformat(),
        )
        self.state[SESSION_KEY] = asdict(user)
        return user

    def get_current_user(self) -> AuthUser | None:
        """Return current valid user or None."""

        payload = self.state.get(SESSION_KEY)
        if not payload:
            return None
        user = AuthUser(**payload)
        if not self.validate_session(user):
            self.destroy_session()
            return None
        now = datetime.now(timezone.utc)
        self.state[SESSION_KEY] = {**payload, "last_access_at": now.isoformat()}
        return AuthUser(**self.state[SESSION_KEY])

    def validate_session(self, user: AuthUser) -> bool:
        """Validate session age."""

        last_access = datetime.fromisoformat(user.last_access_at)
        return datetime.now(timezone.utc) - last_access <= timedelta(seconds=self.ttl_seconds)

    def destroy_session(self) -> None:
        """Destroy active session."""

        self.state.pop(SESSION_KEY, None)

