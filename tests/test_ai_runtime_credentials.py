import os

from src.ai.runtime_credentials import (
    ai_connection_status,
    clear_ai_credentials,
    has_ai_credentials,
    mask_key,
    save_ai_credentials,
    validate_api_key,
)


def test_mask_key_does_not_expose_full_secret():
    masked = mask_key("sk-proj-abcdefghijklmnopqrstuvwxyz")

    assert masked.startswith("sk-pro")
    assert masked.endswith("wxyz")
    assert "abcdefghijklmnopqrstuv" not in masked


def test_save_openai_credentials_sets_environment(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    session = {}

    ok, message = save_ai_credentials(session, "openai", "sk-proj-test123456", "gpt-4o-mini")

    assert ok
    assert "OpenAI" in message
    assert os.getenv("OPENAI_API_KEY") == "sk-proj-test123456"
    assert session["runtime_openai_model"] == "gpt-4o-mini"


def test_clear_anthropic_credentials_removes_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
    session = {"runtime_anthropic_api_key": "sk-ant-test123"}

    clear_ai_credentials(session, "anthropic")

    assert "runtime_anthropic_api_key" not in session
    assert os.getenv("ANTHROPIC_API_KEY") is None


def test_invalid_keys_are_rejected():
    assert not validate_api_key("openai", "bad-key")[0]
    assert not validate_api_key("anthropic", "bad-key")[0]


def test_connection_status_masks_session_key():
    status = ai_connection_status({"runtime_openai_api_key": "sk-proj-abcdef123456"})

    assert status["openai"]["status"] == "Conectado"
    assert status["openai"]["key"] != "sk-proj-abcdef123456"


def test_has_ai_credentials_checks_session_and_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert not has_ai_credentials({})
    assert has_ai_credentials({"runtime_openai_api_key": "sk-proj-test"})
