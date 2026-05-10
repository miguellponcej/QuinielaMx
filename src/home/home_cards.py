"""Streamlit card rendering for active draws Home."""

from __future__ import annotations

import streamlit as st

from src.home.home_recommendations import can_generate_prediction, recommended_action, requires_manual_load


BADGE_LABELS = {
    "Recomendado": "Estado: recomendado",
    "Moderado": "Estado: moderado",
    "No prioritario": "Estado: no prioritario",
    "Solo informativo": "Estado: solo informativo",
}


def render_draw_card(draw: dict, key_prefix: str = "draw") -> dict | None:
    """Render one draw card and return the selected action."""

    rec = draw.get("recommendation", {})
    badge = BADGE_LABELS.get(rec.get("recommendation", ""), "Estado: dato no disponible")
    can_predict = can_generate_prediction(draw)
    needs_manual = requires_manual_load(draw)
    with st.container(border=True):
        st.markdown(f"### {draw.get('game_name', 'Dato no disponible')}")
        st.caption(badge)
        cols = st.columns(4)
        cols[0].metric("Estado", draw.get("status", "Dato no disponible"))
        cols[1].metric("Calidad", f"{draw.get('data_quality_score', 0)}/100")
        cols[2].metric("Score", f"{rec.get('recommendation_score', 0)}/100")
        cols[3].metric("Prediccion directa", "Si" if can_predict else "No")
        st.write(
            {
                "Fecha sorteo": draw.get("draw_date", "Dato no disponible"),
                "Fecha limite": draw.get("closing_date", "Dato no disponible"),
                "Premio/bolsa": draw.get("estimated_prize") or draw.get("accumulated_pool") or "Dato no disponible",
                "Costo": draw.get("cost_per_entry", "Dato no disponible"),
                "Fuente": draw.get("official_url", "Dato no disponible"),
                "Requiere mas datos web": "Si" if needs_manual else "No",
            }
        )
        st.info(rec.get("reason", "Dato no disponible"))
        action = recommended_action(draw)
        if st.button(action, key=f"{key_prefix}_{draw.get('game_id')}"):
            return {
                "game_id": str(draw.get("game_id")),
                "action": action,
                "can_generate_prediction": can_predict,
            }
    return None


def render_missing_data(draws: list[dict]) -> None:
    """Render missing data section."""

    st.subheader("Datos faltantes")
    rows = []
    for draw in draws:
        missing = draw.get("missing_fields", [])
        errors = draw.get("source_errors", [])
        if missing or errors or (draw.get("game_type") == "sports_pool" and not draw.get("matches")):
            if draw.get("game_type") == "sports_pool" and not draw.get("matches"):
                missing = [*missing, "partidos estructurados"]
            rows.append(
                {
                    "juego": draw.get("game_name"),
                    "faltantes": ", ".join(dict.fromkeys(missing)) if missing else "Ninguno",
                    "fuente_no_respondio": ", ".join(errors) if errors else "Ninguna",
                    "accion": "Actualizar fuentes web/cache o activar conector web automatizado",
                }
            )
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.success("No hay datos faltantes registrados.")
