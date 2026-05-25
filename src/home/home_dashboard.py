"""Private active draws Home dashboard flow."""

from __future__ import annotations

from collections.abc import Callable

from src.active_draws.active_draws_service import get_active_draws
from src.active_draws.official_sources_client import OfficialSourcesClient
from src.audit.provenance import PredictionTrace, build_manual_trace
from src.auth.auth_service import AuthService
from src.auth.session_manager import AuthUser
from src.config.games import RiskProfile
from src.home.home_recommendations import (
    best_quality_draws,
    build_decision_rows,
    manual_load_required,
    next_closing_draw,
    ready_for_prediction,
    sort_recommendations,
)
from src.realtime.real_time_prediction_pipeline import real_time_prediction_pipeline


def load_active_draws_home_dashboard(
    auth_service: AuthService,
    force_refresh: bool = False,
    progress_callback: Callable[[str, int | None], None] | None = None,
) -> dict:
    """Load active draws Home data after auth validation."""

    user = auth_service.require_authorized_email()
    try:
        client = OfficialSourcesClient(progress_callback=progress_callback) if progress_callback else None
    except TypeError:
        client = OfficialSourcesClient()
        if progress_callback:
            progress_callback("Modo compatibilidad: cliente de fuentes sin progreso interno.", None)
    try:
        return get_active_draws(
            force_refresh=force_refresh,
            user_email=user.email,
            client=client,
            progress_callback=progress_callback,
        )
    except TypeError:
        if progress_callback:
            progress_callback("Modo compatibilidad: servicio de sorteos sin progreso interno.", None)
        return get_active_draws(
            force_refresh=force_refresh,
            user_email=user.email,
            client=client,
        )


def build_home_view_model(payload: dict, user: AuthUser) -> dict:
    """Build a UI-friendly Home view model."""

    draws = payload.get("draws", [])
    ready = ready_for_prediction(draws)
    manual = manual_load_required(draws)
    best_quality = best_quality_draws(draws)
    next_closing = next_closing_draw(draws)
    return {
        "welcome": f"Bienvenido, {user.name}",
        "updated_at": payload.get("updated_at", "Dato no disponible"),
        "connection_status": _connection_status(payload, ready),
        "summary": payload.get("summary", {}),
        "draws": draws,
        "recommended": sort_recommendations(draws),
        "decision_rows": build_decision_rows(draws),
        "ready_for_prediction": ready,
        "manual_required": manual,
        "best_quality": best_quality,
        "next_to_close": next_closing,
        "decision_center": {
            "ready_count": len(ready),
            "manual_count": len(manual),
            "best_quality_game": best_quality[0].get("game_name") if best_quality else "Dato no disponible",
            "next_closing_game": next_closing.get("game_name") if next_closing else "Dato no disponible",
            "next_closing_date": next_closing.get("closing_date") if next_closing else "Dato no disponible",
        },
        "errors": payload.get("errors", []),
        "source_diagnostics": payload.get("source_diagnostics", []),
        "used_cache": payload.get("used_cache", False),
}


def _connection_status(payload: dict, ready: list[dict]) -> str:
    if ready and payload.get("used_cache"):
        return "Cache con partidos estructurados"
    if ready:
        return "Fuentes web con partidos estructurados"
    if payload.get("used_cache"):
        return "Cache/local"
    return "Fuentes web consultadas"


def generate_real_time_prediction(
    game_type: str,
    matches: list[dict],
    budget: float,
    risk_profile: str = RiskProfile.BALANCED.value,
    trace: PredictionTrace | None = None,
) -> dict:
    """Generate prediction from an active draw card when structured matches exist."""

    if not matches:
        return {
            "status": "missing_data",
            "message": "No hay partidos estructurados disponibles en fuentes web/cache. No se generara prediccion.",
        }
    trace = trace or build_manual_trace(
        internal_file_paths=["active_draws_home_dashboard"],
        web_locations=["fuente registrada desde Home"],
        incomplete_data=["Momios, lesiones y forma avanzada no estan disponibles en fuentes web estructuradas."],
        model_variables=["probabilidades_modelo", "entropia", "riesgo"],
    )
    result = real_time_prediction_pipeline(
        game_type=game_type,
        quiniela=matches,
        trace=trace,
        budget=budget,
        risk_profile=risk_profile,
        n_matches=len(matches),
    )
    return {
        "status": "ok",
        "predictions": result.predictions,
        "ticket": result.ticket,
        "trace": trace,
    }
