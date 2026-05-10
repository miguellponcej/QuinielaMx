"""Application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXAMPLES_DATA_DIR = DATA_DIR / "examples"


@dataclass(frozen=True)
class Settings:
    """Runtime settings."""

    random_seed: int = int(os.getenv("QUINIELA_RANDOM_SEED", "42"))
    monte_carlo_scenarios: int = int(os.getenv("QUINIELA_MONTE_CARLO_SCENARIOS", "100000"))
    default_cost: float = float(os.getenv("QUINIELA_DEFAULT_COST", "15"))


settings = Settings()

