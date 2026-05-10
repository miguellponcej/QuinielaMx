"""Local data connectors for manual and semi-automatic updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config.games import GameConfig
from src.data.cleaners import clean_quiniela_frame, clean_results_frame
from src.data.loaders import load_table, save_processed
from src.data.validators import (
    validate_american_football_results,
    validate_historical_quiniela_results,
    validate_market_probabilities,
    validate_quiniela_df,
    validate_soccer_results,
)


@dataclass(frozen=True)
class DataLoadResult:
    """Loaded and validated data result."""

    name: str
    frame: pd.DataFrame
    processed_path: Path | None = None


class LocalDataConnector:
    """Read CSV/Excel files, validate them and optionally save processed copies."""

    def __init__(self, processed_dir: str | Path | None = None) -> None:
        self.processed_dir = Path(processed_dir) if processed_dir else None

    def load_soccer_results(self, path: str | Path, save_as: str | None = None) -> DataLoadResult:
        """Load historical soccer results."""

        frame = clean_results_frame(load_table(path))
        validate_soccer_results(frame)
        return self._result("soccer_results", frame, save_as)

    def load_football_results(self, path: str | Path, save_as: str | None = None) -> DataLoadResult:
        """Load historical NFL/NCAA results."""

        frame = clean_results_frame(load_table(path))
        validate_american_football_results(frame)
        return self._result("football_results", frame, save_as)

    def load_market_probabilities(
        self,
        path: str | Path,
        game_config: GameConfig,
        save_as: str | None = None,
    ) -> DataLoadResult:
        """Load manually captured market probabilities."""

        frame = load_table(path).copy()
        frame.columns = [str(col).strip().lower() for col in frame.columns]
        validate_market_probabilities(frame, game_config)
        return self._result("market_probabilities", frame, save_as)

    def load_current_quiniela(
        self,
        path: str | Path,
        game_config: GameConfig,
        save_as: str | None = None,
    ) -> DataLoadResult:
        """Load current Progol/Protouch quiniela."""

        frame = clean_quiniela_frame(load_table(path))
        validate_quiniela_df(frame, game_config)
        return self._result("current_quiniela", frame, save_as)

    def load_historical_quiniela_results(
        self,
        path: str | Path,
        game_config: GameConfig,
        save_as: str | None = None,
    ) -> DataLoadResult:
        """Load historical Progol/Revancha/Protouch official results."""

        frame = load_table(path).copy()
        frame.columns = [str(col).strip().lower() for col in frame.columns]
        validate_historical_quiniela_results(frame, game_config)
        return self._result("historical_quiniela_results", frame, save_as)

    def _result(self, name: str, frame: pd.DataFrame, save_as: str | None) -> DataLoadResult:
        processed_path = None
        if save_as:
            if self.processed_dir is None:
                raise ValueError("processed_dir is required when save_as is provided.")
            processed_path = save_processed(frame, self.processed_dir / save_as)
        return DataLoadResult(name=name, frame=frame, processed_path=processed_path)

