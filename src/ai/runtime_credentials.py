"""Runtime AI credentials for the private Streamlit session.

Keys are never written to disk by this module. In Streamlit, they are kept in
session state and mirrored to process environment variables so the extraction
clients can use them during the same private session.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from typing import Any


OPENAI_KEY_SESSION = "runtime_openai_api_key"
OPENAI_MODEL_SESSION = "runtime_openai_model"
ANTHROPIC_KEY_SESSION = "runtime_anthropic_api_key"
ANTHROPIC_MODEL_SESSION = "runtime_anthropic_model"
AI_EXTRACTION_SESSION = "runtime_enable_ai_extraction"


def apply_session_ai_credentials(session_state: MutableMapping[str, Any]) -> None:
    """Apply Streamlit session AI keys to runtime environment."""

    openai_key = str(session_state.get(OPENAI_KEY_SESSION, "") or "").strip()
    anthropic_key = str(session_state.get(ANTHROPIC_KEY_SESSION, "") or "").strip()
    openai_model = str(session_state.get(OPENAI_MODEL_SESSION, "") or "").strip()
    anthropic_model = str(session_state.get(ANTHROPIC_MODEL_SESSION, "") or "").strip()
    enable_ai = session_state.get(AI_EXTRACTION_SESSION)
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    if openai_model:
        os.environ["OPENAI_MODEL"] = openai_model
    if anthropic_model:
        os.environ["ANTHROPIC_MODEL"] = anthropic_model
    if enable_ai is not None:
        os.environ["ENABLE_AI_EXTRACTION"] = "true" if bool(enable_ai) else "false"


def save_ai_credentials(
    session_state: MutableMapping[str, Any],
    provider: str,
    api_key: str,
    model: str = "",
) -> tuple[bool, str]:
    """Validate and save one provider key in session state."""

    provider = provider.lower().strip()
    api_key = api_key.strip()
    valid, message = validate_api_key(provider, api_key)
    if not valid:
        return False, message
    if provider == "openai":
        session_state[OPENAI_KEY_SESSION] = api_key
        if model.strip():
            session_state[OPENAI_MODEL_SESSION] = model.strip()
    elif provider == "anthropic":
        session_state[ANTHROPIC_KEY_SESSION] = api_key
        if model.strip():
            session_state[ANTHROPIC_MODEL_SESSION] = model.strip()
    else:
        return False, "Proveedor no soportado."
    apply_session_ai_credentials(session_state)
    return True, f"{provider_name(provider)} activado para esta sesion."


def clear_ai_credentials(session_state: MutableMapping[str, Any], provider: str) -> None:
    """Remove one provider key from session and environment."""

    provider = provider.lower().strip()
    if provider == "openai":
        session_state.pop(OPENAI_KEY_SESSION, None)
        os.environ.pop("OPENAI_API_KEY", None)
    elif provider == "anthropic":
        session_state.pop(ANTHROPIC_KEY_SESSION, None)
        os.environ.pop("ANTHROPIC_API_KEY", None)


def ai_connection_status(session_state: MutableMapping[str, Any] | None = None) -> dict[str, dict[str, str]]:
    """Return masked status for UI."""

    session_state = session_state or {}
    openai_key = str(session_state.get(OPENAI_KEY_SESSION) or os.getenv("OPENAI_API_KEY") or "")
    anthropic_key = str(session_state.get(ANTHROPIC_KEY_SESSION) or os.getenv("ANTHROPIC_API_KEY") or "")
    return {
        "openai": {
            "provider": "ChatGPT / OpenAI",
            "status": "Conectado" if bool(openai_key) else "No conectado",
            "key": mask_key(openai_key),
            "model": str(session_state.get(OPENAI_MODEL_SESSION) or os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        },
        "anthropic": {
            "provider": "Claude / Anthropic",
            "status": "Conectado" if bool(anthropic_key) else "No conectado",
            "key": mask_key(anthropic_key),
            "model": str(session_state.get(ANTHROPIC_MODEL_SESSION) or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")),
        },
    }


def validate_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Validate key shape without making a paid API call."""

    if not api_key:
        return False, "Ingresa una API key."
    provider = provider.lower().strip()
    if provider == "openai" and not api_key.startswith(("sk-", "sk-proj-")):
        return False, "La API key de OpenAI normalmente inicia con sk- o sk-proj-."
    if provider == "anthropic" and not api_key.startswith("sk-ant-"):
        return False, "La API key de Claude/Anthropic normalmente inicia con sk-ant-."
    return True, "Formato valido."


def mask_key(api_key: str) -> str:
    """Mask a key for display."""

    if not api_key:
        return "No configurada"
    if len(api_key) <= 10:
        return "*" * len(api_key)
    return f"{api_key[:6]}...{api_key[-4:]}"


def provider_name(provider: str) -> str:
    return {"openai": "OpenAI", "anthropic": "Claude"}.get(provider, provider)
