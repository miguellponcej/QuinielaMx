"""Streamlit card rendering for active draws Home."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

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
        cols = st.columns(5)
        cols[0].metric("No. juego", draw.get("draw_number", "Dato no disponible"))
        cols[1].metric("Estado", _display_status(draw.get("status")))
        cols[2].metric("Calidad", f"{draw.get('data_quality_score', 0)}/100")
        cols[3].metric("Score", f"{rec.get('recommendation_score', 0)}/100")
        cols[4].metric("Listo", "Si" if can_predict else "No")
        d1, d2, d3 = st.columns(3)
        d1.caption("Fecha de celebracion")
        d1.write(draw.get("draw_date", "Dato no disponible"))
        d2.caption("Fecha limite")
        d2.write(draw.get("closing_date", "Dato no disponible"))
        d3.caption("Premio/bolsa")
        d3.write(draw.get("estimated_prize") or draw.get("accumulated_pool") or "Dato no disponible")
        d4, d5, d6 = st.columns(3)
        d4.caption("Costo")
        d4.write(draw.get("cost_per_entry", "Dato no disponible"))
        d5.caption("Fuente principal")
        d5.write(draw.get("official_url", "Dato no disponible"))
        d6.caption("Estado de datos")
        d6.write("Accionable" if can_predict else "Bloqueado" if needs_manual else "Informativo")
        if draw.get("matches"):
            st.caption(f"Partidos estructurados detectados: {len(draw.get('matches', []))}")
        elif draw.get("candidate_matches"):
            st.warning(
                "Se descartaron partidos de calendario general porque no coinciden con la quiniela oficial vigente."
            )
        has_reference = bool(draw.get("source_artifacts") or draw.get("alternate_sources"))
        render_official_reference(draw, expanded=bool(has_reference and not can_predict))
        if draw.get("source_warnings"):
            with st.expander("Notas de fuente"):
                for warning in draw.get("source_warnings", []):
                    st.write(f"- {warning}")
        st.info(rec.get("reason", "Dato no disponible"))
        action = recommended_action(draw)
        if st.button(action, key=f"{key_prefix}_{draw.get('game_id')}", type="primary" if can_predict else "secondary"):
            return {
                "game_id": str(draw.get("game_id")),
                "action": action,
                "can_generate_prediction": can_predict,
            }
    return None


def render_missing_data(draws: list[dict]) -> None:
    """Render missing data section."""

    st.subheader("Datos por mejorar")
    rows = []
    for draw in draws:
        missing = draw.get("missing_fields", [])
        errors = draw.get("source_errors", [])
        blocking = requires_manual_load(draw)
        if missing or errors or (draw.get("game_type") == "sports_pool" and not draw.get("matches")):
            if draw.get("game_type") == "sports_pool" and not draw.get("matches"):
                missing = [*missing, "partidos estructurados"]
            rows.append(
                {
                    "juego": draw.get("game_name"),
                    "numero_juego": draw.get("draw_number", "Dato no disponible"),
                    "fecha_celebracion": draw.get("draw_date", "Dato no disponible"),
                    "impacto": "Bloquea prediccion" if blocking else "Opcional / mejora calidad",
                    "faltantes": ", ".join(dict.fromkeys(missing)) if missing else "Ninguno",
                    "fuente_no_respondio": ", ".join(errors) if errors else "Ninguna",
                    "accion": "Actualizar fuentes web" if blocking else "No impide predecir",
                }
            )
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.success("No hay datos faltantes registrados.")


def _display_status(value: object) -> str:
    """Return status text that is easy to understand in the UI."""

    return {
        "active": "Vigente",
        "closed": "Cerrado",
        "Vigente": "Vigente",
        "Dato no disponible": "Dato no disponible",
    }.get(str(value), str(value or "Dato no disponible"))


def render_official_reference(draw: dict, expanded: bool = True) -> None:
    """Render official contest image or guide reference."""

    artifacts = [item for item in draw.get("source_artifacts", []) if isinstance(item, dict) and item.get("url")]
    image_artifacts = [
        item
        for item in artifacts
        if str(item.get("type", "")).lower() == "image"
        or str(item.get("url", "")).lower().split("?")[0].endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    pdf_artifacts = [
        item
        for item in artifacts
        if str(item.get("type", "")).lower() == "pdf" or ".pdf" in str(item.get("url", "")).lower()
    ]
    guide_sources = list(
        dict.fromkeys(
            [
                item["url"]
                for item in pdf_artifacts
                if item.get("url")
            ]
            + [
                source
                for source in draw.get("alternate_sources", [])
                if isinstance(source, str) and (source.lower().endswith(".pdf") or ".pdf?" in source.lower())
            ]
        )
    )
    official_url = draw.get("official_url")
    if not image_artifacts and not guide_sources and not official_url:
        return
    with st.expander("Referencia oficial del concurso", expanded=expanded):
        st.caption("Referencia tomada de la pagina oficial consultada para este juego.")
        if image_artifacts:
            first_image = image_artifacts[0]
            st.image(
                first_image["url"],
                caption="Imagen oficial publicada por Pronosticos/Loteria Nacional",
                use_container_width=True,
            )
            if len(image_artifacts) > 1:
                st.caption(f"Hay {len(image_artifacts)} imagenes oficiales registradas.")
        if guide_sources:
            st.markdown("**Guia oficial vigente**")
            st.caption("Si la vista previa no carga en este navegador, abre la guia oficial con el boton.")
            components.iframe(guide_sources[0], height=560, scrolling=True)
            for idx, url in enumerate(guide_sources, start=1):
                st.link_button(f"Abrir guia oficial {idx}", url)
        if official_url:
            st.link_button("Abrir pagina oficial consultada", str(official_url))
