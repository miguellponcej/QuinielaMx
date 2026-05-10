"""Descriptive analysis for random lottery draws."""

from __future__ import annotations

import numpy as np
import pandas as pd


RANDOM_DRAW_WARNING = (
    "Los sorteos aleatorios no tienen memoria estadistica confiable para prediccion causal. "
    "Las frecuencias historicas describen el pasado, no aumentan la probabilidad real de un numero futuro "
    "si el sorteo esta correctamente aleatorizado."
)


def analyze_random_draws(df: pd.DataFrame, number_columns: list[str]) -> dict[str, pd.DataFrame | str]:
    """Return descriptive random draw analysis."""

    numbers = df[number_columns].melt(value_name="numero")["numero"].dropna().astype(int)
    frequency = numbers.value_counts().sort_index().rename_axis("numero").reset_index(name="frecuencia")
    mean_freq = frequency["frecuencia"].mean()
    frequency["temperatura"] = np.where(
        frequency["frecuencia"] > mean_freq,
        "caliente",
        np.where(frequency["frecuencia"] < mean_freq, "frio", "neutral"),
    )
    parity = pd.DataFrame(
        {
            "tipo": ["pares", "impares"],
            "conteo": [int((numbers % 2 == 0).sum()), int((numbers % 2 == 1).sum())],
        }
    )
    ranges = pd.cut(numbers, bins=[0, 10, 20, 30, 40, 50, 60], include_lowest=True).value_counts().sort_index()
    ranges_df = ranges.rename_axis("rango").reset_index(name="conteo")
    repetitions = (
        df[number_columns]
        .apply(lambda row: len(row.dropna()) - len(set(row.dropna().astype(int))), axis=1)
        .value_counts()
        .sort_index()
        .rename_axis("repeticiones_en_sorteo")
        .reset_index(name="conteo")
    )
    return {
        "advertencia": RANDOM_DRAW_WARNING,
        "frecuencias": frequency,
        "pares_impares": parity,
        "rangos": ranges_df,
        "repeticiones": repetitions,
    }


def monte_carlo_random_draw(
    universe_size: int,
    draw_size: int,
    tickets: int,
    scenarios: int = 100_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Visualize random draw hit distributions for uniformly sampled tickets."""

    rng = np.random.default_rng(seed)
    hits = []
    universe = np.arange(1, universe_size + 1)
    for _ in range(scenarios):
        winning = set(rng.choice(universe, size=draw_size, replace=False))
        best = 0
        for _ticket in range(tickets):
            ticket = set(rng.choice(universe, size=draw_size, replace=False))
            best = max(best, len(winning & ticket))
        hits.append(best)
    values, counts = np.unique(hits, return_counts=True)
    return pd.DataFrame({"aciertos": values, "escenarios": counts, "probabilidad": counts / scenarios})

