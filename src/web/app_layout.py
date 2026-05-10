"""Shared Streamlit layout helpers."""

from __future__ import annotations

from src.auth.session_manager import AuthUser


def user_label(user: AuthUser) -> str:
    """Return a compact authenticated user label."""

    return f"{user.name} <{user.email}>"

