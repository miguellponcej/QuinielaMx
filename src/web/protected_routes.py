"""Named protected application sections."""

from __future__ import annotations

from src.auth.auth_service import AuthService
from src.auth.session_manager import AuthUser

PROTECTED_SECTIONS = {
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


def is_protected_section(section: str) -> bool:
    """Return whether a section must require auth."""

    return section in PROTECTED_SECTIONS


def require_protected_route(auth_service: AuthService, section: str) -> AuthUser:
    """Require auth for a named protected section."""

    if is_protected_section(section):
        return auth_service.require_authorized_email()
    raise PermissionError(f"Unknown or unprotected section: {section}")
