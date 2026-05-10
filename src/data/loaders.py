"""Load quinielas, results and odds from local files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def load_table(path: str | Path) -> pd.DataFrame:
    """Load a CSV, Excel or JSON file as a DataFrame."""

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {suffix}")
    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    with file_path.open("r", encoding="utf-8") as handle:
        payload: Any = json.load(handle)
    return pd.DataFrame(payload)


def save_processed(df: pd.DataFrame, path: str | Path) -> Path:
    """Save a processed table as CSV."""

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    return file_path


def load_quiniela(path: str | Path) -> list[dict[str, Any]]:
    """Load a quiniela file into list-of-dicts records."""

    df = load_table(path)
    return df.to_dict(orient="records")

