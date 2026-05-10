"""Normalize raw quiniela or results files into data/processed."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import PROCESSED_DATA_DIR
from src.data.cleaners import clean_quiniela_frame, clean_results_frame
from src.data.loaders import load_table, save_processed

app = typer.Typer(help="Normalize raw data files for QuinielaPredictor MX.")


@app.command()
def quiniela(input_path: Path, output_name: str = "quiniela_limpia.csv") -> None:
    """Normalize a quiniela file."""

    df = clean_quiniela_frame(load_table(input_path))
    output = save_processed(df, PROCESSED_DATA_DIR / output_name)
    typer.echo(f"Saved {output}")


@app.command()
def results(input_path: Path, output_name: str = "resultados_limpios.csv") -> None:
    """Normalize a historical results file."""

    df = clean_results_frame(load_table(input_path))
    output = save_processed(df, PROCESSED_DATA_DIR / output_name)
    typer.echo(f"Saved {output}")


if __name__ == "__main__":
    app()

