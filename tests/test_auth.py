from pathlib import Path

from src.auth.auth_config import AuthConfig
from src.auth.auth_service import AuthService, hash_password


def _config(password: str = "secret") -> AuthConfig:
    return AuthConfig(
        app_env="production",
        app_secret_key="app-secret",
        authorized_emails=("miguellponcej@gmail.com",),
        google_client_id="",
        google_client_secret="",
        session_secret="session-secret",
        auth_password_hash=hash_password(password),
        session_ttl_seconds=28800,
        enable_ip_allowlist=False,
        allowed_ips=(),
        log_level="INFO",
    )


def test_authorized_user_can_login_and_logout():
    state = {}
    auth = AuthService(_config(), state)

    ok, _ = auth.login("miguellponcej@gmail.com", "secret")

    assert ok
    assert auth.is_authenticated()
    assert auth.get_current_user().email == "miguellponcej@gmail.com"
    auth.logout()
    assert not auth.is_authenticated()


def test_unauthorized_user_is_blocked():
    auth = AuthService(_config(), {})

    ok, message = auth.login("intruso@example.com", "secret")

    assert not ok
    assert "no autorizado" in message.lower()


def test_authorized_emails_env_parsing(monkeypatch):
    monkeypatch.setenv("AUTHORIZED_EMAILS", "miguellponcej@gmail.com,otro@example.com")

    config = AuthConfig.from_env()

    assert "miguellponcej@gmail.com" in config.authorized_emails
    assert "otro@example.com" in config.authorized_emails


def test_unauthorized_attempt_is_logged():
    log_path = Path("data/security_logs/security_access.log")
    before = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    auth = AuthService(_config(), {})

    auth.login("intruso@example.com", "secret")

    after = log_path.read_text(encoding="utf-8")
    assert len(after) > len(before)
    assert "unauthorized_email" in after

