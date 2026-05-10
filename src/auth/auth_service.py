"""Authentication service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import MutableMapping
from typing import Any

from src.auth.auth_config import AuthConfig
from src.auth.session_manager import AuthUser, SessionManager
from src.security.audit_log import security_log
from src.security.ip_allowlist import is_ip_allowed
from src.security.rate_limit import RateLimiter


PASSWORD_ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 210_000


class AuthService:
    """Login, logout, authorization and session validation."""

    def __init__(
        self,
        config: AuthConfig,
        state: MutableMapping[str, Any],
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.config = config
        self.session_manager = SessionManager(state, ttl_seconds=config.session_ttl_seconds)
        self.rate_limiter = rate_limiter or RateLimiter()

    def login(
        self,
        email: str,
        password: str,
        ip: str = "unknown",
        user_agent: str = "unknown",
    ) -> tuple[bool, str]:
        """Authenticate and create a session."""

        normalized_email = email.strip().lower()
        key = f"{normalized_email}:{ip}"
        if self.rate_limiter.is_blocked(key):
            security_log(normalized_email, "login", "blocked_rate_limit", ip, user_agent)
            return False, "Demasiados intentos. Intenta mas tarde."
        if not is_ip_allowed(ip, self.config.enable_ip_allowlist, self.config.allowed_ips):
            security_log(normalized_email, "login", "blocked_ip", ip, user_agent)
            return False, "IP no autorizada."
        if not self.is_authorized_user(normalized_email):
            self.rate_limiter.register_failure(key)
            security_log(normalized_email, "login", "unauthorized_email", ip, user_agent)
            return False, "Acceso no autorizado."
        if not self.config.auth_password_hash:
            security_log(normalized_email, "login", "missing_password_hash", ip, user_agent)
            return False, "AUTH_PASSWORD_HASH no esta configurado."
        if not verify_password(password, self.config.auth_password_hash):
            self.rate_limiter.register_failure(key)
            security_log(normalized_email, "login", "invalid_password", ip, user_agent)
            return False, "Credenciales invalidas."
        self.rate_limiter.register_success(key)
        self.create_session(normalized_email, name=_display_name(normalized_email))
        security_log(normalized_email, "login", "success", ip, user_agent)
        return True, "Login exitoso."

    def logout(self, ip: str = "unknown", user_agent: str = "unknown") -> None:
        """Logout current user."""

        user = self.get_current_user()
        security_log(user.email if user else "unknown", "logout", "success", ip, user_agent)
        self.destroy_session()

    def get_current_user(self) -> AuthUser | None:
        """Return current user."""

        return self.session_manager.get_current_user()

    def is_authenticated(self) -> bool:
        """Return whether a user is authenticated."""

        return self.get_current_user() is not None

    def is_authorized_user(self, email: str) -> bool:
        """Validate email against AUTHORIZED_EMAILS."""

        return email.strip().lower() in set(self.config.authorized_emails)

    def require_auth(self) -> AuthUser:
        """Return current user or raise PermissionError."""

        user = self.get_current_user()
        if user is None:
            security_log("unknown", "protected_route", "unauthenticated")
            raise PermissionError("Authentication required.")
        return user

    def require_authorized_email(self) -> AuthUser:
        """Return user if authorized, otherwise raise PermissionError."""

        user = self.require_auth()
        if not self.is_authorized_user(user.email):
            security_log(user.email, "protected_route", "unauthorized_email")
            raise PermissionError("Authorized email required.")
        return user

    def validate_session(self) -> bool:
        """Return whether current session is valid."""

        return self.get_current_user() is not None

    def create_session(self, email: str, name: str = "") -> AuthUser:
        """Create a user session."""

        return self.session_manager.create_session(email, name)

    def destroy_session(self) -> None:
        """Destroy current session."""

        self.session_manager.destroy_session()


def hash_password(password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a PBKDF2-SHA256 password hash suitable for AUTH_PASSWORD_HASH."""

    raw_salt = salt.encode("utf-8") if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), raw_salt, iterations)
    salt_b64 = base64.b64encode(raw_salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{PASSWORD_ALGORITHM}${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a PBKDF2-SHA256 password hash."""

    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _display_name(email: str) -> str:
    if email == "miguellponcej@gmail.com":
        return "Miguel Angel"
    return email.split("@")[0]
