"""Decorators for protected functions."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from src.auth.auth_service import AuthService


F = TypeVar("F", bound=Callable[..., Any])


def require_auth(auth_service: AuthService) -> Callable[[F], F]:
    """Protect a function with auth service validation."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            auth_service.require_authorized_email()
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator

