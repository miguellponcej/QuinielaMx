from pathlib import Path

import pandas as pd
import pytest

from src.auth.auth_config import AuthConfig
from src.auth.auth_service import AuthService, hash_password
from src.audit.provenance import build_manual_trace
from src.config.games import GameType
from src.prediction.predictor import QuinielaPredictor
from src.web.protected_routes import require_protected_route


def test_sensitive_files_are_not_configured_as_public():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    nginx = Path("deploy/nginx.conf").read_text(encoding="utf-8")

    for path in ["data/raw/", "data/processed/", "data/security_logs/", "data/access_logs/", ".env"]:
        assert path in gitignore
    assert "data/raw" in nginx
    assert "data/security_logs" in nginx
    assert "deny all" in nginx


def test_prediction_flow_requires_valid_session_before_execution():
    auth = AuthService(
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
        {},
    )

    with pytest.raises(PermissionError):
        require_protected_route(auth, "Prediccion en tiempo real")

    auth.login("miguellponcej@gmail.com", "secret")
    require_protected_route(auth, "Prediccion en tiempo real")
    df = pd.read_csv("data/examples/progol_quiniela.csv")
    market = pd.read_csv("data/examples/progol_market_probs.csv")
    trace = build_manual_trace(
        ["data/examples/progol_quiniela.csv", "data/examples/progol_market_probs.csv"],
        ["https://www.loterianacional.gob.mx/Home/Resultados"],
        model_variables=["probabilidades", "mercado"],
    )

    predictions = QuinielaPredictor(GameType.PROGOL).predict(df, market_probs=market, trace=trace)

    assert predictions
