"""Environment-based secret and configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Mapping


def load_env_file(path: str | Path = ".env", override: bool = False) -> None:
    """Load simple KEY=VALUE pairs from a local .env file.

    This intentionally supports only the subset used by this project and keeps
    real environment variables authoritative by default.
    """

    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


def load_mapping_to_env(values: Mapping[str, object], override: bool = False) -> None:
    """Load Streamlit/cloud secrets into environment variables."""

    for key, value in values.items():
        name = str(key).strip()
        if not name or value is None:
            continue
        if override or name not in os.environ:
            os.environ[name] = str(value)


def get_env(name: str, default: str = "") -> str:
    """Read an environment variable."""

    return os.getenv(name, default)


def get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_csv_env(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable."""

    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]
