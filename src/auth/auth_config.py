"""Authentication configuration."""

from __future__ import annotations

from dataclasses import dataclass

from src.security.secrets import get_bool_env, get_csv_env, get_env


@dataclass(frozen=True)
class AuthConfig:
    """Auth and session settings loaded from environment variables."""

    app_env: str
    app_secret_key: str
    authorized_emails: tuple[str, ...]
    google_client_id: str
    google_client_secret: str
    session_secret: str
    auth_password_hash: str
    session_ttl_seconds: int
    enable_ip_allowlist: bool
    allowed_ips: tuple[str, ...]
    log_level: str

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Build config from environment."""

        return cls(
            app_env=get_env("APP_ENV", "production"),
            app_secret_key=get_env("APP_SECRET_KEY"),
            authorized_emails=tuple(email.lower() for email in get_csv_env("AUTHORIZED_EMAILS")),
            google_client_id=get_env("GOOGLE_CLIENT_ID"),
            google_client_secret=get_env("GOOGLE_CLIENT_SECRET"),
            session_secret=get_env("SESSION_SECRET"),
            auth_password_hash=get_env("AUTH_PASSWORD_HASH"),
            session_ttl_seconds=int(get_env("SESSION_TTL_SECONDS", "28800")),
            enable_ip_allowlist=get_bool_env("ENABLE_IP_ALLOWLIST", False),
            allowed_ips=tuple(get_csv_env("ALLOWED_IPS")),
            log_level=get_env("LOG_LEVEL", "INFO"),
        )

    @property
    def is_production(self) -> bool:
        """Return whether production protections should be strict."""

        return self.app_env.lower() == "production"

