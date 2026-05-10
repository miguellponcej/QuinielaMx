"""Rules for recommendation labels and actions."""

from __future__ import annotations


def classify_recommendation(draw: dict, score: int) -> tuple[str, str, str, str]:
    """Return recommendation, action, risk level and button label."""

    if draw.get("game_type") == "random_lottery":
        if score >= 60:
            return "Solo informativo", "Ver analisis", "Alto", "Ver solo informacion"
        return "Solo informativo", "Revisar despues", "Alto", "Ver solo informacion"
    if score > 70:
        return "Recomendado", "Analizar quiniela", "Medio", "Generar prediccion"
    if 50 <= score <= 70:
        return "Moderado", "Generar jugada con cautela", "Medio", "Actualizar fuentes web"
    return "No prioritario", "Revisar despues", "Alto", "Actualizar fuentes web"
