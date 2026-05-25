"""Private Streamlit interface for QuinielaPredictor MX."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.security.secrets import load_env_file, load_mapping_to_env

load_env_file(PROJECT_ROOT / ".env")
try:
    load_mapping_to_env(st.secrets)
except Exception:
    pass

from src.audit.provenance import MODEL_VERSION, build_manual_trace
from src.auth.auth_config import AuthConfig
from src.auth.auth_service import AuthService
from src.auth.session_manager import AuthUser
from src.config.games import GameType, OptimizationGoal, RiskProfile, get_game_config
from src.home.home_cards import render_draw_card, render_missing_data, render_official_reference
from src.home.home_dashboard import (
    build_home_view_model,
    generate_real_time_prediction,
    load_active_draws_home_dashboard,
)
from src.lottery.random_draw_analysis import RANDOM_DRAW_WARNING
from src.history.evaluator import evaluate_prediction_run, summarize_model_performance
from src.history.storage import load_evaluation_history, load_prediction_history, record_prediction_run
from src.optimization.low_cost_optimizer import optimize_low_cost_ticket
from src.optimization.monte_carlo import MonteCarloSimulator
from src.optimization.ticket_optimizer import TicketOptimizer
from src.realtime.real_time_prediction_pipeline import real_time_prediction_pipeline
from src.security.audit_log import security_log
from src.security.private_policy import assert_private_by_default
from src.web.app_layout import user_label


st.set_page_config(page_title="QuinielaPredictor MX", layout="wide")
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stJson {display: none;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_request_context() -> tuple[str, str]:
    """Best-effort IP and user-agent extraction for Streamlit."""

    try:
        headers = getattr(st, "context", None).headers  # type: ignore[union-attr]
        ip = headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
        user_agent = headers.get("user-agent", "unknown")
        return ip or "unknown", user_agent or "unknown"
    except Exception:
        return "unknown", "unknown"


def game_from_label(label: str) -> GameType:
    """Map UI label to game type."""

    return {
        "Progol": GameType.PROGOL,
        "Progol Revancha": GameType.PROGOL_REVANCHA,
        "Progol Media Semana": GameType.PROGOL_MEDIA_SEMANA,
        "Protouch": GameType.PROTOUCH,
        "Sorteos aleatorios": GameType.RANDOM_DRAW,
    }[label]


def game_id_from_type(game_type: GameType) -> str:
    """Map game type to active draw id."""

    return {
        GameType.PROGOL: "progol",
        GameType.PROGOL_REVANCHA: "progol_revancha",
        GameType.PROGOL_MEDIA_SEMANA: "progol_media_semana",
        GameType.PROTOUCH: "protouch",
        GameType.RANDOM_DRAW: "random_draw",
    }[game_type]


def find_draw_for_game(draws: list[dict], game_type: GameType) -> dict | None:
    """Find the active draw record for a selected game."""

    game_id = game_id_from_type(game_type)
    if game_type == GameType.RANDOM_DRAW:
        return next((draw for draw in draws if draw.get("game_type") == "random_lottery"), None)
    return next((draw for draw in draws if draw.get("game_id") == game_id), None)


def build_web_trace(draw: dict | None, payload: dict) -> object:
    """Build trace from web/cache sources only."""

    web_locations = list(dict.fromkeys(payload.get("sources", [])))
    if draw and draw.get("official_url") not in (None, "", "Dato no disponible"):
        web_locations.append(draw["official_url"])
    if draw:
        web_locations.extend(draw.get("alternate_sources", []) or [])
    web_locations = list(dict.fromkeys(web_locations)) or ["active_draws_service"]
    incomplete = []
    if draw:
        incomplete.extend(draw.get("missing_fields", []))
        incomplete.extend(draw.get("source_errors", []))
        incomplete.extend(draw.get("source_warnings", []))
    return build_manual_trace(
        internal_file_paths=["data/active_draws/cache/active_draws_cache.json"],
        web_locations=web_locations,
        fresh_data=[f"Fuentes web consultadas; cache usado={payload.get('used_cache', False)}."],
        incomplete_data=incomplete or ["Sin faltantes registrados por el servicio web."],
        discarded_data=payload.get("errors", []),
        model_variables=[
            "probabilidades_modelo",
            "probabilidades_mercado_si_disponibles_web",
            "entropia",
            "brecha_top1_top2",
            "riesgo",
        ],
    )


def show_login(auth: AuthService) -> None:
    """Render login screen only."""

    st.title("QuinielaPredictor MX")
    st.caption("Aplicacion privada. Inicia sesion para continuar.")
    with st.form("login_form"):
        email = st.text_input("Correo autorizado")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar sesion")
    if submitted:
        ip, user_agent = get_request_context()
        ok, message = auth.login(email, password, ip=ip, user_agent=user_agent)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)


def show_access_denied(auth: AuthService, user: AuthUser) -> None:
    """Render access denied without sensitive data."""

    ip, user_agent = get_request_context()
    security_log(user.email, "access_denied", "unauthorized_email", ip, user_agent)
    st.title("Acceso no autorizado")
    st.error("Tu cuenta no esta autorizada para acceder a esta aplicacion.")
    if st.button("Cerrar sesion"):
        auth.logout(ip, user_agent)
        st.rerun()


def render_header(auth: AuthService, user: AuthUser) -> None:
    """Render private header and logout controls."""

    ip, user_agent = get_request_context()
    with st.sidebar:
        st.caption("Sesion privada")
        st.write(user_label(user))
        st.caption(f"Ultimo acceso: {user.last_access_at}")
        if st.button("Cerrar sesion"):
            auth.logout(ip, user_agent)
            st.rerun()


def show_private_app(auth: AuthService, user: AuthUser) -> None:
    """Render the private application after successful auth."""

    render_header(auth, user)
    st.title("QuinielaPredictor MX")
    st.caption(
        "Prediccion probabilistica, optimizacion de cobertura y simulacion. "
        "No garantiza premios; cuantifica incertidumbre."
    )

    with st.sidebar:
        game_label = st.selectbox(
            "Juego",
            ["Progol", "Progol Revancha", "Progol Media Semana", "Protouch", "Sorteos aleatorios"],
        )
        game_type = game_from_label(game_label)
        budget = st.number_input("Presupuesto maximo", min_value=10.0, value=600.0, step=10.0)
        scenarios = st.number_input("Escenarios Monte Carlo", min_value=1000, max_value=200000, value=100000, step=1000)
        page = st.radio(
            "Pantalla",
            ["Home", "Dashboard", "Prediccion", "Optimizacion", "Simulacion", "Historicos", "Configuracion"],
        )

    if page == "Home":
        render_home(auth, user, budget=budget)
        return

    if game_type == GameType.RANDOM_DRAW:
        render_random_draw_page(auth)
        return

    config = get_game_config(game_type)
    with st.sidebar:
        force_web_refresh = st.button("Actualizar fuentes web", key="sidebar_web_refresh")

    payload = load_active_draws_home_dashboard(auth, force_refresh=force_web_refresh)
    selected_draw = find_draw_for_game(payload.get("draws", []), game_type)
    trace = build_web_trace(selected_draw, payload)

    if not selected_draw or not selected_draw.get("matches"):
        if selected_draw:
            render_official_reference(selected_draw, expanded=True)
        render_web_data_unavailable(config, selected_draw, payload, trace)
        if page == "Configuracion":
            render_configuration(user, auth.config, trace)
        return

    quiniela_df = pd.DataFrame(selected_draw["matches"]).head(config.n_matches)
    market_df = None

    realtime_result = real_time_prediction_pipeline(
        game_type=game_type,
        quiniela=quiniela_df,
        market_probs=market_df,
        trace=trace,
        budget=budget,
        n_matches=len(quiniela_df),
    )
    save_prediction_history_once(realtime_result, game_id_from_type(game_type), selected_draw)
    predictions = realtime_result.predictions
    prediction_df = realtime_result.prediction_frame
    if page in {"Dashboard", "Prediccion", "Optimizacion", "Simulacion"}:
        render_official_reference(selected_draw, expanded=True)

    if page == "Dashboard":
        render_dashboard(config, quiniela_df, trace)
    elif page == "Prediccion":
        security_log(user.email, "prediction_execution", "success")
        render_prediction(config, predictions, prediction_df)
    elif page == "Optimizacion":
        render_optimization(config, predictions, budget)
    elif page == "Simulacion":
        render_simulation(config, predictions, budget, scenarios)
    elif page == "Historicos":
        render_historics(config)
    elif page == "Configuracion":
        render_configuration(user, auth.config, trace)


def render_random_draw_page(auth: AuthService) -> None:
    """Render random draw analysis page."""

    st.warning(RANDOM_DRAW_WARNING)
    force_refresh = st.button("Actualizar sorteos aleatorios desde web")
    payload = load_active_draws_home_dashboard(auth, force_refresh=force_refresh)
    random_draws = [draw for draw in payload.get("draws", []) if draw.get("game_type") == "random_lottery"]
    if random_draws:
        st.dataframe(
            [
                {
                    "juego": draw.get("game_name"),
                    "estado": draw.get("status"),
                    "sorteo": draw.get("draw_number"),
                    "fecha": draw.get("draw_date"),
                    "premio_bolsa": draw.get("estimated_prize") or draw.get("accumulated_pool"),
                    "fuente": draw.get("official_url"),
                    "calidad": draw.get("data_quality_score"),
                }
                for draw in random_draws
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No se encontraron sorteos aleatorios estructurados en fuentes web/cache.")
    st.info(
        "El analisis historico descriptivo requiere que la fuente web publique historicos estructurados. "
        "No se solicitaran cargas manuales y no se predicen numeros ganadores."
    )


def render_web_data_unavailable(config, draw: dict | None, payload: dict, trace) -> None:
    """Explain why a web-only prediction cannot run yet."""

    st.subheader(f"{config.name}: prediccion pendiente")
    st.info(
        "Ya se consultaron las fuentes oficiales y de mercado disponibles. Para emitir una prediccion confiable, "
        "la quiniela debe estar disponible como partidos con local, visitante, liga y fecha. Si la fuente oficial "
        "solo publica imagen o guia, se muestra como evidencia, pero no se sustituyen datos con calendarios genericos."
    )
    st.warning(
        "Siguiente accion: presiona Actualizar fuentes web cuando el concurso se publique en formato legible. "
        "La app no inventa partidos ni momios."
    )
    if draw:
        st.dataframe(
            [
                {
                    "juego": draw.get("game_name"),
                    "fuente": draw.get("official_url"),
                    "actualizado": draw.get("last_updated"),
                    "frescura": draw.get("data_freshness"),
                    "calidad": draw.get("data_quality_score"),
                    "faltantes": _human_missing_fields(draw.get("missing_fields", [])) or "Ninguno",
                    "notas": _friendly_source_notes(draw) or "Fuente consultada; esperando datos estructurados.",
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
    if payload.get("errors"):
        with st.expander("Errores de fuentes web"):
            for error in payload["errors"]:
                st.write(f"- {error}")
    with st.expander("Estado de fuentes web"):
        render_source_diagnostics(payload.get("source_diagnostics", []), show_title=False)
    with st.expander("Trazabilidad registrada"):
        render_trace_summary(trace)


def render_dashboard(config, quiniela_df: pd.DataFrame, trace) -> None:
    """Render private dashboard."""

    st.subheader("Dashboard principal")
    c1, c2, c3 = st.columns(3)
    c1.metric("Juego", config.name)
    c2.metric("Partidos", len(quiniela_df))
    c3.metric("Costo por combinacion", f"${config.cost_per_combination:,.0f}")
    st.write("Quiniela cargada")
    st.dataframe(quiniela_df, use_container_width=True)
    with st.expander("Trazabilidad de datos registrada"):
        render_trace_summary(trace)


def render_prediction(config, predictions, prediction_df: pd.DataFrame) -> None:
    """Render prediction page."""

    st.subheader("Prediccion por partido")
    executive_cols = [
        "id",
        "local",
        "visitante",
        "momios",
        "fuente_momio",
        "linea_mercado",
        "lectura_favorito",
        "lectura_riesgo",
        "lectura_recomendacion",
        "lectura_cobertura_sugerida",
        "recomendacion_final",
        "mensaje_ejecutivo",
    ]
    st.dataframe(prediction_df[[column for column in executive_cols if column in prediction_df.columns]], use_container_width=True)
    with st.expander("Factores ejecutivos por partido"):
        for prediction in predictions:
            st.markdown(f"**Partido {prediction.id}: {prediction.local} vs {prediction.visitante}**")
            st.write(prediction.executive_explanation.mensaje)
            st.dataframe(
                [
                    {"bloque": "Lectura rapida", **prediction.executive_explanation.lectura_rapida},
                    {"bloque": "Factores", **prediction.executive_explanation.factores},
                ],
                use_container_width=True,
                hide_index=True,
            )
    prob_cols = [f"prob_{option.lower()}" for option in config.options]
    chart_df = prediction_df[["id", *prob_cols]].melt("id", var_name="resultado", value_name="probabilidad")
    fig = px.bar(chart_df, x="id", y="probabilidad", color="resultado", barmode="group")
    st.plotly_chart(fig, use_container_width=True)


def render_optimization(config, predictions, budget: float) -> None:
    """Render optimization page."""

    st.subheader("Optimizacion de quiniela")
    risk = st.selectbox("Perfil de riesgo", [item.value for item in RiskProfile], index=1)
    goal = st.selectbox("Preferencia", [item.value for item in OptimizationGoal])
    max_doubles = st.number_input("Maximo dobles", min_value=0, max_value=config.n_matches, value=min(5, config.n_matches))
    max_triples = st.number_input("Maximo triples", min_value=0, max_value=config.n_matches, value=min(1, config.n_matches))
    optimizer = TicketOptimizer(config)
    ticket = optimizer.optimize(
        predictions,
        budget=budget,
        risk_profile=risk,
        max_doubles=int(max_doubles),
        max_triples=int(max_triples),
        goal=goal,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Combinaciones", ticket.combinations)
    c2.metric("Costo total", f"${ticket.cost:,.0f}")
    c3.metric("Prob. cubierta completa", f"{ticket.probability_all_correct:.4%}")
    display_cols = [
        "partido",
        "seleccion_fija",
        "cobertura_recomendada",
        "probabilidad_principal",
        "riesgo",
        "motivo_cobertura",
    ]
    st.dataframe(ticket.table[display_cols], use_container_width=True)
    with st.expander("Diagnostico marginal de coberturas"):
        st.dataframe(ticket.marginal_steps, use_container_width=True)
    st.subheader("Estrategias de bajo costo")
    strategies = optimize_low_cost_ticket(predictions, config, budget)
    st.dataframe(strategies.resumen, use_container_width=True)
    scenario_label = st.selectbox(
        "Ver escenario",
        ["economico", "balanceado", "agresivo", "personalizado"],
        index=1,
    )
    scenario_ticket = getattr(strategies, scenario_label)
    st.dataframe(scenario_ticket.table[display_cols], use_container_width=True)


def render_simulation(config, predictions, budget: float, scenarios: int) -> None:
    """Render Monte Carlo page."""

    st.subheader("Simulacion Monte Carlo")
    strategies = optimize_low_cost_ticket(predictions, config, budget)
    strategy_name = st.selectbox("Estrategia", ["economico", "balanceado", "agresivo", "personalizado"])
    ticket = getattr(strategies, strategy_name)
    simulator = MonteCarloSimulator(config)
    result = simulator.simulate(predictions, ticket.selections, scenarios=int(scenarios))
    st.dataframe(result.summary, use_container_width=True)
    fig = px.bar(result.hits_distribution, x="aciertos", y="probabilidad")
    st.plotly_chart(fig, use_container_width=True)


def render_historics(config) -> None:
    """Render historical/backtesting page."""

    st.subheader("Historicos y backtesting")
    performance = summarize_model_performance()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Predicciones evaluadas", performance["runs"])
    c2.metric("Partidos comparados", performance["matches"])
    c3.metric("Accuracy directa", f"{performance['accuracy']:.1%}")
    c4.metric("Accuracy con cobertura", f"{performance['coverage_accuracy']:.1%}")
    if performance["brier_score"] is not None:
        st.metric("Brier score promedio", f"{performance['brier_score']:.4f}")

    predictions = load_prediction_history()
    evaluations = load_evaluation_history()
    if predictions:
        st.write("Predicciones guardadas")
        st.dataframe(
            [
                {
                    "run_id": item.get("run_id"),
                    "juego": item.get("game_name"),
                    "numero": item.get("draw_number"),
                    "fecha": item.get("draw_date"),
                    "creada": item.get("created_at"),
                    "partidos": len(item.get("predictions", [])),
                    "modelo": item.get("model_version"),
                }
                for item in predictions[-50:]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aun no hay predicciones guardadas en el historial privado.")
    if st.button("Comparar predicciones guardadas contra resultados oficiales"):
        try:
            evaluation = evaluate_prediction_run()
            st.success(f"Evaluacion creada: {evaluation.direct_hits}/{evaluation.total_matches} aciertos directos.")
            st.dataframe(evaluation.match_rows, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.warning(f"No hay comparacion disponible todavia: {exc}")
    if evaluations:
        st.write("Evaluaciones historicas")
        st.dataframe(evaluations[-50:], use_container_width=True, hide_index=True)
    st.caption(
        "El aprendizaje del modelo se activa automaticamente cuando existen suficientes concursos comparados "
        "contra resultados oficiales. No se sobreajusta con muestras pequenas."
    )


def render_home(auth: AuthService, user: AuthUser, budget: float = 600.0) -> None:
    """Render active draws smart Home."""

    st.subheader("Home")
    col_a, col_b = st.columns([3, 1])
    force_refresh = col_b.button("Actualizar sorteos vigentes")
    payload = load_home_payload_with_progress(auth, force_refresh=force_refresh)
    model = build_home_view_model(payload, user)
    col_a.markdown(f"### {model['welcome']}")
    st.caption(f"Ultima actualizacion: {model['updated_at']} | Estado: {model['connection_status']}")
    if model["used_cache"] and not model["ready_for_prediction"]:
        st.warning("No fue posible actualizar fuentes web o se uso cache vigente. Se muestran datos de cache/locales.")
    elif model["used_cache"]:
        st.info("Se esta usando cache vigente con partidos estructurados. Puedes generar prediccion y actualizar fuentes cuando quieras.")
    if model["errors"]:
        with st.expander("Errores de fuentes"):
            for error in model["errors"]:
                st.write(f"- {error}")
    render_next_action(model)
    summary = model["summary"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Juegos", summary.get("total_games", 0))
    c2.metric("Listos para predecir", len(model["ready_for_prediction"]))
    c3.metric("Quinielas", summary.get("sports_pools", 0))
    c4.metric("Sorteos", summary.get("random_lotteries", 0))
    c5.metric("Recomendados", summary.get("recommended_games", 0))

    st.subheader("Centro de decision")
    decision = model["decision_center"]
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Listos para predecir", decision.get("ready_count", 0))
    d2.metric("Pendientes de datos", decision.get("manual_count", 0))
    d3.metric("Mejor calidad", decision.get("best_quality_game", "Dato no disponible"))
    d4.metric("Cierra primero", decision.get("next_closing_game", "Dato no disponible"))
    st.caption(f"Fecha de cierre mas proxima: {decision.get('next_closing_date', 'Dato no disponible')}")

    if model["decision_rows"]:
        cols = [
            "prioridad",
            "juego",
            "numero_juego",
            "fecha_celebracion",
            "tipo",
            "estado",
            "cierre",
            "calidad_datos",
            "recomendacion",
            "score",
            "accion_sugerida",
            "prediccion_directa",
        ]
        st.dataframe(model["decision_rows"], use_container_width=True, hide_index=True, column_order=cols)
    else:
        st.info("No se encontraron sorteos o quinielas vigentes en fuentes oficiales, cache o archivos locales.")

    if model["ready_for_prediction"]:
        st.subheader("Listos para generar prediccion")
        st.success("Estos juegos ya tienen partidos estructurados desde fuentes web/cache. Puedes generar prediccion desde sus tarjetas.")
        ready_rows = [
            {
                "juego": draw.get("game_name"),
                "numero_juego": draw.get("draw_number", "Dato no disponible"),
                "fecha_celebracion": draw.get("draw_date", "Dato no disponible"),
                "calidad_datos": draw.get("data_quality_score"),
                "cierre": draw.get("closing_date", "Dato no disponible"),
                "partidos": len(draw.get("matches", [])),
                "accion": "Generar prediccion desde Home",
            }
            for draw in model["ready_for_prediction"]
        ]
        st.dataframe(ready_rows, use_container_width=True, hide_index=True)

    if model["manual_required"]:
        st.subheader("Pendientes de datos web")
        manual_rows = [
            {
                "juego": draw.get("game_name"),
                "numero_juego": _display_value(draw.get("draw_number")),
                "fecha_celebracion": _display_value(draw.get("draw_date")),
                "faltantes": _human_missing_fields(draw.get("missing_fields", [])) or "partidos oficiales en formato legible",
                "accion": "Actualizar fuentes web",
            }
            for draw in model["manual_required"]
        ]
        st.dataframe(manual_rows, use_container_width=True, hide_index=True)

    st.subheader("Juegos priorizados")
    selected_action = None
    selected_draw = None
    for draw in model["recommended"]:
        action = render_draw_card(draw, key_prefix="home")
        if action:
            selected_action = action
            selected_draw = draw
    if selected_action and selected_draw:
        st.session_state["selected_active_game_id"] = selected_action["game_id"]
        st.session_state["selected_home_action"] = selected_action["action"]
        if selected_action["can_generate_prediction"]:
            st.info(
                "Referencia: "
                f"No. juego {selected_draw.get('draw_number', 'Dato no disponible')} | "
                f"Fecha de celebracion {selected_draw.get('draw_date', 'Dato no disponible')}"
            )
            result = generate_real_time_prediction(
                selected_action["game_id"],
                selected_draw.get("matches", []),
                budget=budget,
                trace=build_web_trace(selected_draw, payload),
            )
            if result.get("status") == "ok":
                home_history_result = SimpleNamespace(
                    game_config=get_game_config(
                        game_from_label(selected_draw.get("game_name", "Progol")),
                        n_matches=len(selected_draw.get("matches", [])),
                    ),
                    predictions=result["predictions"],
                    ticket=result["ticket"],
                    trace=result["trace"],
                    data_quality_notes=["Prediccion generada desde Home."],
                )
                save_prediction_history_once(home_history_result, selected_action["game_id"], selected_draw)
            _render_home_prediction_result(result)
        else:
            st.warning(
                "Este juego todavia requiere datos web estructurados o solo permite analisis informativo. "
                "Revisa la seccion de datos faltantes para completarlo."
            )
    render_missing_data(model["draws"])
    with st.expander("Estado de fuentes web consultadas"):
        render_source_diagnostics(model.get("source_diagnostics", []), show_title=False)


def render_next_action(model: dict) -> None:
    """Show the main action in plain language before detailed tables."""

    ready = model.get("ready_for_prediction", [])
    if ready:
        best = ready[0]
        st.success(
            "Siguiente accion recomendada: genera prediccion para "
            f"{best.get('game_name', 'el juego disponible')} "
            f"(No. {best.get('draw_number', 'Dato no disponible')}, "
            f"fecha {best.get('draw_date', 'Dato no disponible')})."
        )
        return
    manual = model.get("manual_required", [])
    if manual:
        st.warning(
            "Las quinielas deportivas estan detectadas, pero aun falta informacion estructurada para predecir. "
            "Revisa la referencia oficial y actualiza fuentes web antes de generar jugadas."
        )
        return
    st.info("No hay una accion prioritaria en este momento. Revisa sorteos informativos o actualiza fuentes.")


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


def _display_value(value: object) -> str:
    if value in (None, "", "Dato no disponible"):
        return "Pendiente"
    return str(value)


def _friendly_source_notes(draw: dict) -> str:
    notes = []
    if draw.get("source_artifacts"):
        notes.append("Referencia visual oficial registrada.")
    if draw.get("alternate_sources"):
        notes.append("Guia o fuente alterna oficial registrada.")
    if draw.get("source_warnings"):
        notes.extend(str(item) for item in draw.get("source_warnings", []))
    return " ".join(notes)


def load_home_payload_with_progress(auth: AuthService, force_refresh: bool) -> dict:
    """Load Home payload with visible progress feedback."""

    if not force_refresh:
        with st.spinner("Cargando sorteos vigentes y recomendaciones..."):
            return load_active_draws_home_dashboard(auth, force_refresh=False)

    progress_text = st.empty()
    progress_bar = st.progress(0)
    progress_text.write("Validando sesion privada...")
    progress_bar.progress(15)
    progress_text.write("Consultando fuentes oficiales, cache y fuentes deportivas estructuradas...")
    progress_bar.progress(35)
    payload = load_active_draws_home_dashboard(auth, force_refresh=True)
    progress_text.write("Validando frescura, datos faltantes y partidos estructurados...")
    progress_bar.progress(70)
    progress_text.write("Calculando recomendaciones y prioridad de analisis...")
    progress_bar.progress(90)
    progress_bar.progress(100)
    progress_text.success("Actualizacion terminada.")
    return payload


def render_source_diagnostics(diagnostics: list[dict], show_title: bool = True) -> None:
    """Render trusted source status for the Home dashboard."""

    if show_title:
        st.subheader("Estado de fuentes web")
    if not diagnostics:
        st.info("No hay diagnostico de fuentes disponible en esta ejecucion.")
        return
    rows = []
    for source in diagnostics:
        rows.append(
            {
                "fuente": source.get("name", "Dato no disponible"),
                "tipo": source.get("category", "Dato no disponible"),
                "datos": ", ".join(source.get("data_types", [])),
                "estado": source.get("status", "Dato no disponible"),
                "acceso": source.get("access_mode", "Dato no disponible"),
                "prioridad": source.get("priority", 0),
                "nota": source.get("notes", ""),
                "error": source.get("error", ""),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "Las casas de apuestas y APIs de momios se usan solo como referencia de mercado cuando el acceso es permitido "
        "y estructurado. Si una fuente bloquea o exige clave, queda registrada y no se inventan partidos ni momios."
    )


def _render_home_prediction_result(result: dict) -> None:
    """Render direct Home prediction output."""

    if result.get("status") != "ok":
        st.warning(result.get("message", "No fue posible generar la prediccion desde Home."))
        return
    predictions = result["predictions"]
    ticket = result["ticket"]
    rows = [
        {
            "partido": f"{prediction.local} vs {prediction.visitante}",
            "recomendacion": prediction.recommendation,
            "cobertura": "/".join(prediction.coverage),
            "confianza": prediction.confidence,
            "riesgo": prediction.risk,
            "momios": prediction.as_dict().get("momios"),
            "fuente_momio": prediction.market_source or "Dato no disponible",
            "linea_mercado": prediction.as_dict().get("linea_mercado"),
            "explicacion": prediction.explanation,
        }
        for prediction in predictions
    ]
    st.success("Prediccion generada desde Home con trazabilidad registrada.")
    t1, t2, t3 = st.columns(3)
    t1.metric("Combinaciones", ticket.combinations)
    t2.metric("Costo", f"${ticket.cost:,.2f}")
    t3.metric("Prob. quiniela completa", f"{ticket.probability_all_correct:.4%}")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.dataframe(ticket.table, use_container_width=True, hide_index=True)


def save_prediction_history_once(realtime_result, game_id: str, draw: dict | None) -> None:
    """Save one prediction run once per Streamlit session state."""

    draw_key = str((draw or {}).get("draw_number", "sin_numero"))
    key = f"history_saved_{game_id}_{draw_key}_{realtime_result.trace.generated_at}"
    if st.session_state.get(key):
        return
    try:
        record_prediction_run(realtime_result, game_id=game_id, draw=draw)
        st.session_state[key] = True
    except Exception as exc:
        st.caption(f"No se pudo guardar historial de prediccion: {exc}")


def render_trace_summary(trace) -> None:
    """Render traceability without raw JSON blocks."""

    data = trace.as_dict()
    internal_files = [source.get("name", "") for source in data.get("internal_files", [])]
    web_sources = [source.get("location", source.get("name", "")) for source in data.get("web_sources", [])]
    rows = [
        {"categoria": "Archivos internos", "detalle": ", ".join(internal_files) or "Ninguno"},
        {"categoria": "Fuentes web", "detalle": ", ".join(web_sources) or "Ninguna"},
        {"categoria": "Datos frescos", "detalle": ", ".join(data.get("fresh_data", [])) or "No confirmado"},
        {"categoria": "Datos incompletos", "detalle": ", ".join(data.get("incomplete_data", [])) or "Ninguno"},
        {"categoria": "Datos descartados", "detalle": ", ".join(data.get("discarded_data", [])) or "Ninguno"},
        {"categoria": "Variables del modelo", "detalle": ", ".join(data.get("model_variables", [])) or "No disponible"},
        {"categoria": "Version del modelo", "detalle": data.get("model_version", "Dato no disponible")},
        {"categoria": "Fecha", "detalle": data.get("generated_at", "Dato no disponible")},
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_configuration(user: AuthUser, config: AuthConfig, trace) -> None:
    """Render private configuration/admin page."""

    st.subheader("Configuracion")
    st.dataframe(
        [
            {"campo": "Usuario", "valor": user.name},
            {"campo": "Correo", "valor": user.email},
            {"campo": "Ultimo acceso", "valor": user.last_access_at},
            {"campo": "Correos autorizados", "valor": ", ".join(config.authorized_emails)},
            {"campo": "Ultima prediccion", "valor": trace.generated_at},
            {"campo": "Version del modelo", "valor": MODEL_VERSION},
            {
                "campo": "Estado de seguridad",
                "valor": "Autenticacion activa, lista blanca de correos, logs y sesiones con expiracion.",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.info("Los usuarios autorizados se controlan desde AUTHORIZED_EMAILS. No se agregan usuarios desde la interfaz.")


def main() -> None:
    """Authenticate before rendering any private content."""

    assert_private_by_default()
    auth = AuthService(AuthConfig.from_env(), st.session_state)
    user = auth.get_current_user()
    if not user:
        show_login(auth)
        return
    if not auth.is_authorized_user(user.email):
        show_access_denied(auth, user)
        return
    show_private_app(auth, user)


if __name__ == "__main__":
    main()
