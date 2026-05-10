"""Data normalization helpers."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize_team_name(value: object) -> str:
    """Normalize team names for matching across sources."""

    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def clean_quiniela_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized quiniela DataFrame."""

    frame = df.copy()
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    if "id" not in frame.columns:
        frame.insert(0, "id", range(1, len(frame) + 1))
    for column in ("local", "visitante", "liga"):
        if column in frame.columns:
            frame[column] = frame[column].astype(str).str.strip()
            frame[f"{column}_key"] = frame[column].map(normalize_team_name)
    if "fecha" in frame.columns:
        frame["fecha"] = pd.to_datetime(frame["fecha"], errors="coerce").dt.date.astype("string")
    return frame


def clean_results_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized historical results DataFrame."""

    frame = df.copy()
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    if "fecha" in frame.columns:
        frame["fecha"] = pd.to_datetime(frame["fecha"], errors="coerce")
    for column in ("local", "visitante"):
        if column in frame.columns:
            frame[f"{column}_key"] = frame[column].map(normalize_team_name)
    return frame

