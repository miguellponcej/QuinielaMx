from src.audit.provenance import build_manual_trace


def sample_trace():
    return build_manual_trace(
        internal_file_paths=["data/examples/progol_quiniela.csv", "data/examples/progol_market_probs.csv"],
        web_locations=[
            "https://www.loterianacional.gob.mx/Home/Resultados",
            "https://www.loterianacional.gob.mx/DatosAbiertos/NumerosGanadores",
        ],
        fresh_data=["Datos de ejemplo cargados para prueba."],
        incomplete_data=["Sin lesiones ni forma avanzada."],
        model_variables=["probabilidades", "mercado", "entropia", "riesgo"],
    )

