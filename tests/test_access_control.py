import pytest

from src.auth.auth_config import AuthConfig
from src.auth.auth_service import AuthService, hash_password
from src.web.protected_routes import PROTECTED_SECTIONS, require_protected_route


def _auth(state):
    return AuthService(
        AuthConfig(
            app_env="production",
            app_secret_key="app-secret",
            authorized_emails=("miguellponcej@gmail.com",),
            google_client_id="",
            google_client_secret="",
            session_secret="session-secret",
            auth_password_hash=hash_password("secret"),
            session_ttl_seconds=28800,
            enable_ip_allowlist=False,
            allowed_ips=(),
            log_level="INFO",
        ),
        state,
    )


def test_unauthenticated_user_cannot_access_protected_route():
    auth = _auth({})

    with pytest.raises(PermissionError):
        require_protected_route(auth, "Dashboard principal")


def test_authenticated_authorized_user_can_access_protected_route():
    state = {}
    auth = _auth(state)
    auth.login("miguellponcej@gmail.com", "secret")

    user = require_protected_route(auth, "Dashboard principal")

    assert user.email == "miguellponcej@gmail.com"


def test_all_sensitive_sections_are_protected():
    expected = {
        "Dashboard principal",
        "Prediccion en tiempo real",
        "Carga de archivos",
        "Consulta de historicos",
        "Optimizacion de quiniela",
        "Simulacion Monte Carlo",
        "Logs de prediccion",
        "Panel de fuentes",
        "Configuracion",
        "APIs internas",
        "Descarga de reportes",
    }

    assert expected.issubset(PROTECTED_SECTIONS)

