"""Create Excel templates for manual data capture."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "data" / "templates"


TEMPLATES: dict[str, pd.DataFrame] = {
    "quiniela_progol": pd.DataFrame(
        {
            "id": range(1, 15),
            "local": ["" for _ in range(14)],
            "visitante": ["" for _ in range(14)],
            "liga": ["" for _ in range(14)],
            "fecha": ["" for _ in range(14)],
        }
    ),
    "quiniela_protouch": pd.DataFrame(
        {
            "id": range(1, 14),
            "local": ["" for _ in range(13)],
            "visitante": ["" for _ in range(13)],
            "liga": ["NFL" for _ in range(13)],
            "fecha": ["" for _ in range(13)],
        }
    ),
    "probabilidades_mercado_progol": pd.DataFrame(
        {"id": range(1, 15), "prob_l": ["" for _ in range(14)], "prob_e": ["" for _ in range(14)], "prob_v": ["" for _ in range(14)]}
    ),
    "probabilidades_mercado_protouch": pd.DataFrame(
        {"id": range(1, 14), "prob_l": ["" for _ in range(13)], "prob_d": ["" for _ in range(13)], "prob_v": ["" for _ in range(13)]}
    ),
    "resultados_soccer": pd.DataFrame(
        {
            "fecha": [""],
            "local": [""],
            "visitante": [""],
            "goles_local": [""],
            "goles_visitante": [""],
            "liga": [""],
            "temporada": [""],
        }
    ),
    "resultados_nfl_ncaa": pd.DataFrame(
        {
            "fecha": [""],
            "local": [""],
            "visitante": [""],
            "puntos_local": [""],
            "puntos_visitante": [""],
            "liga": [""],
            "temporada": [""],
        }
    ),
    "historico_progol": pd.DataFrame(
        {"sorteo": [""], "fecha": [""], "resultado": ["LEVVLL..."], "producto": ["Progol"]}
    ),
    "historico_protouch": pd.DataFrame(
        {"sorteo": [""], "fecha": [""], "resultado": ["DDLVD..."], "producto": ["Protouch"]}
    ),
}


def create_templates() -> list[Path]:
    """Create one workbook with all sheets and individual workbooks."""

    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    all_path = TEMPLATE_DIR / "plantillas_captura_manual.xlsx"
    with pd.ExcelWriter(all_path, engine="openpyxl") as writer:
        for sheet_name, frame in TEMPLATES.items():
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    created.append(all_path)
    for name, frame in TEMPLATES.items():
        path = TEMPLATE_DIR / f"{name}.xlsx"
        frame.to_excel(path, index=False)
        created.append(path)
    return created


if __name__ == "__main__":
    for item in create_templates():
        print(item)

