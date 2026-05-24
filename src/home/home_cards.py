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
        cols = st.columns(5)
        cols[0].metric("No. juego", _display_value(draw.get("draw_number")))
        cols[1].metric("Estado", _display_status(draw.get("status")))
        cols[2].metric("Calidad", f"{draw.get('data_quality_score', 0)}/100")
        cols[3].metric("Score", f"{rec.get('recommendation_score', 0)}/100")
        cols[4].metric("Listo", "Si" if can_predict else "No")
        d1, d2, d3 = st.columns(3)
        d1.caption("Fecha de celebracion")
        d1.write(_display_value(draw.get("draw_date")))
        d2.caption("Fecha limite")
        d2.write(_display_value(draw.get("closing_date")))
        d3.caption("Premio/bolsa")
        d3.write(_display_value(draw.get("estimated_prize") or draw.get("accumulated_pool")))
        d4, d5, d6 = st.columns(3)
        d4.caption("Costo")
        d4.write(_display_value(draw.get("cost_per_entry")))
        d5.caption("Fuente principal")
        official_url = draw.get("official_url")
        if official_url and official_url != "Dato no disponible":
            d5.link_button("Abrir fuente oficial", str(official_url))
        else:
            d5.write("Pendiente")
        d6.caption("Estado de datos")
        d6.write("Listo para predecir" if can_predict else "Pendiente de datos web" if needs_manual else "Informativo")
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
        st.info(_product_reason(draw, rec, can_predict, needs_manual))
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
                    "numero_juego": _display_value(draw.get("draw_number")),
                    "fecha_celebracion": _display_value(draw.get("draw_date")),
                    "impacto": "Impide prediccion automatica" if blocking else "Mejora recomendacion",
                    "faltantes": _human_missing_fields(missing) if missing else "Ninguno",
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
        "Dato no disponible": "Pendiente",
    }.get(str(value), str(value or "Pendiente"))


def _display_value(value: object) -> str:
    """Return friendlier text for missing values."""

    if value in (None, "", "Dato no disponible"):
        return "Pendiente"
    return str(value)


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
        st.caption("Evidencia tomada de la fuente oficial consultada para este juego.")
        if image_artifacts:
            first_image = image_artifacts[0]
            st.image(
                first_image["url"],
                caption="Imagen oficial publicada por Pronosticos/Loteria Nacional",
                use_container_width=True,
            )
            if len(image_artifacts) > 1:
                st.caption(f"Hay {len(image_artifacts)} imagenes oficiales registradas.")
            st.success("Referencia visual oficial cargada correctamente.")
        if guide_sources:
            st.markdown("**Guia oficial vigente**")
            st.caption(
                "La guia oficial se abre en una pestaña nueva para evitar bloqueos del navegador. "
                "No se incrusta como iframe externo."
            )
            for idx, url in enumerate(guide_sources, start=1):
                st.link_button(f"Abrir guia oficial {idx}", url)
        if official_url:
            st.link_button("Abrir pagina oficial consultada", str(official_url))


def _human_missing_fields(fields: list[str]) -> str:
    labels = {
        "matches": "partidos oficiales en formato legible",
        "partidos estructurados": "partidos oficiales en formato legible",
        "closing_date": "fecha limite",
        "draw_date": "fecha de celebracion",
        "cost_per_entry": "costo",
        "estimated_prize": "premio",
        "accumulated_pool": "bolsa",
    }
    return ", ".join(dict.fromkeys(labels.get(field, field) for field in fields))


def _product_reason(draw: dict, rec: dict, can_predict: bool, needs_manual: bool) -> str:
    if can_predict:
        return rec.get("reason", "Juego listo para generar una prediccion probabilistica.")
    if draw.get("game_type") == "sports_pool" and needs_manual:
        return (
            "La fuente oficial fue consultada y queda registrada, pero aun falta convertir la quiniela vigente "
            "a partidos estructurados. La app no inventa partidos ni usa calendarios genericos."
        )
    return rec.get("reason", "Informacion disponible para analisis.")
