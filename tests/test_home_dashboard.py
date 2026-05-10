import pytest

from src.auth.auth_config import AuthConfig
from src.auth.auth_service import AuthService, hash_password
from src.auth.session_manager import AuthUser
from src.home.home_dashboard import generate_real_time_prediction, load_active_draws_home_dashboard


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


def test_home_blocks_unauthenticated_user():
    auth = _auth({})

    with pytest.raises(PermissionError):
        load_active_draws_home_dashboard(auth)


def test_generate_prediction_from_sports_card_with_matches():
    matches = [
        {"id": idx, "local": f"Local {idx}", "visitante": f"Visita {idx}", "liga": "Liga", "fecha": "2099-01-01"}
        for idx in range(1, 15)
    ]

    result = generate_real_time_prediction("progol", matches, budget=300)

    assert result["status"] == "ok"
    assert result["predictions"]
    assert result["ticket"].cost <= 300


def test_generate_prediction_from_card_requires_matches():
    result = generate_real_time_prediction("progol", [], budget=300)

    assert result["status"] == "missing_data"


def test_home_view_model_surfaces_decision_center():
    from src.home.home_dashboard import build_home_view_model

    payload = {
        "updated_at": "2099-01-01T00:00:00+00:00",
        "used_cache": False,
        "summary": {"total_games": 2},
        "draws": [
            {
                "game_id": "progol",
                "game_name": "Progol",
                "game_type": "sports_pool",
                "status": "active",
                "closing_date": "2099-01-01T12:00:00+00:00",
                "data_quality_score": 82,
                "matches": [
                    {"id": idx, "local": "A", "visitante": "B", "liga": "Liga", "fecha": "2099-01-01"}
                    for idx in range(1, 15)
                ],
                "recommendation": {"recommendation": "Recomendado", "recommendation_score": 88},
                "missing_fields": [],
                "source_errors": [],
            },
            {
                "game_id": "protouch",
                "game_name": "Protouch",
                "game_type": "sports_pool",
                "status": "active",
                "closing_date": "Dato no disponible",
                "data_quality_score": 45,
                "matches": [],
                "recommendation": {"recommendation": "Moderado", "recommendation_score": 55},
                "missing_fields": ["closing_date"],
                "source_errors": [],
            },
        ],
    }
    user = AuthUser(
        email="miguellponcej@gmail.com",
        name="Miguel Angel",
        login_at="2099-01-01T00:00:00+00:00",
        last_access_at="2099-01-01T00:00:00+00:00",
    )

    model = build_home_view_model(payload, user)

    assert model["decision_center"]["ready_count"] == 1
    assert model["decision_center"]["manual_count"] == 1
    assert model["decision_center"]["best_quality_game"] == "Progol"
    assert model["decision_rows"][0]["juego"] == "Progol"
    assert model["decision_rows"][0]["prediccion_directa"] == "Si"
