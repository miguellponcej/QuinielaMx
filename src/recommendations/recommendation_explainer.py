"""Natural-language explanations for active draw recommendations."""

from __future__ import annotations


def explain_recommendation(draw: dict, score: int) -> str:
    """Generate a concise Home recommendation explanation."""

    name = draw.get("game_name", "Juego")
    if draw.get("game_type") == "random_lottery":
        return (
            f"Solo informativo. {name} puede revisarse por premio, costo e historicos descriptivos; "
            "al ser aleatorio no existe una ventaja predictiva confiable ni se predicen numeros ganadores."
        )
    if score > 70:
        return (
            f"Recomendado. {name} esta vigente o disponible para analisis, tiene informacion suficiente "
            "para una recomendacion probabilistica y la calidad de datos es buena."
        )
    if score >= 50:
        return (
            f"Moderado. {name} puede analizarse, pero faltan datos relevantes como partidos completos, "
            "momios o informacion deportiva reciente; la confianza sera limitada."
        )
    return (
        f"No prioritario. {name} tiene informacion incompleta o no disponible en fuentes web estructuradas. "
        "Conviene actualizar fuentes oficiales/cache antes de generar una prediccion."
    )
