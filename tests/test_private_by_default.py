from pathlib import Path
import os

import pytest

from src.security.private_policy import assert_private_by_default, private_by_default_enabled
from src.security.secrets import load_env_file


def test_private_by_default_env_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("PRIVATE_BY_DEFAULT", raising=False)

    assert private_by_default_enabled()


def test_private_by_default_cannot_be_disabled(monkeypatch):
    monkeypatch.setenv("PRIVATE_BY_DEFAULT", "false")

    with pytest.raises(RuntimeError):
        assert_private_by_default()


def test_no_public_demo_or_public_mode_in_app():
    app = Path("app/streamlit_app.py").read_text(encoding="utf-8").lower()

    forbidden = ["public_demo", "modo publico", "demo publica", "no_auth"]
    assert all(item not in app for item in forbidden)


def test_app_does_not_request_manual_uploads():
    app = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "file_uploader" not in app


def test_docker_image_does_not_copy_example_data():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "COPY data/examples" not in dockerfile


def test_local_env_file_loader_keeps_existing_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=production\nAUTHORIZED_EMAILS=test@example.com\n", encoding="utf-8")
    monkeypatch.setenv("AUTHORIZED_EMAILS", "existing@example.com")

    load_env_file(env_file)

    assert os.environ["AUTHORIZED_EMAILS"] == "existing@example.com"
