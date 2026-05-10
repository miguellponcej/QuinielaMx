"""Access control helpers."""

from __future__ import annotations

from src.auth.auth_service import AuthService
from src.auth.session_manager import AuthUser


def require_private_access(auth_service: AuthService) -> AuthUser:
    """Require authenticated and authorized access."""

    return auth_service.require_authorized_email()

