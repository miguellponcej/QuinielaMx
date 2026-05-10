"""Human-readable prediction explanations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.config.games import GameType, format_outcome
from src.prediction.confidence import risk_score
from src.utils.probability import entropy


@dataclass(frozen=True)
class ExecutiveExplanation:
    """Decision-oriented explanation for one match."""

    lectura_rapida: dict[str, str]
    factores: dict[str, str]
    recomendacion_final: str
    mensaje: str

    def as_dict(self) -> dict[str, object]:
        """Return serializable explanation."""

        return asdict(self)


def explain_prediction(
    game_type: GameType,
    local: str,
    visitante: str,
    probabilities: dict[str, float],
    recommendation: str,
    coverage: list[str],
) -> str:
    """Build a short legacy explanation string."""

    return build_executive_explanation(
        game_type=game_type,
        local=local,
        visitante=visitante,
        probabilities=probabilities,
        recommendation=recommendation,
        coverage=coverage,
        has_market=False,
    ).mensaje


def build_executive_explanation(
    game_type: GameType,
    local: str,
    visitante: str,
    probabilities: dict[str, float],
    recommendation: str,
    coverage: list[str],
    has_market: bool,
) -> ExecutiveExplanation:
    """Build a clear executive explanation for decision-making."""

    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    top_outcome, top_probability = ordered[0]
    second_outcome, second_probability = ordered[1]
    third_probability = ordered[2][1] if len(ordered) > 2 else 0.0
    gap = top_probability - second_probability
    volatility = entropy(list(probabilities.values()))
    risk = risk_score(list(probabilities.values()))
    coverage_type = {1: "Fijo", 2: "Doble", 3: "Triple"}[len(coverage)]
    favorite = _favorite_label(game_type, top_outcome, local, visitante)
    quick = {
        "favorito": f"{favorite} ({top_probability:.0%})",
        "riesgo": _risk_label(risk),
        "recomendacion": format_outcome(game_type, recommendation),
        "cobertura_sugerida": "/".join(format_outcome(game_type, item) for item in coverage),
    }
    factores = {
        "localia": _localia_factor(game_type, top_outcome, local),
        "forma_reciente": _generic_form_factor(gap),
        "diferencial_ofensivo_defensivo": _differential_factor(top_probability, second_probability),
        "historial_entre_equipos": _head_to_head_factor(),
        "mercado": _market_factor(has_market, top_probability, gap),
        "volatilidad": _volatility_factor(volatility, gap, third_probability),
    }
    message = _natural_message(
        game_type=game_type,
        local=local,
        visitante=visitante,
        favorite=favorite,
        coverage_type=coverage_type,
        top_probability=top_probability,
        second_probability=second_probability,
        gap=gap,
        volatility=volatility,
    )
    return ExecutiveExplanation(
        lectura_rapida=quick,
        factores=factores,
        recomendacion_final=coverage_type,
        mensaje=message,
    )


def _favorite_label(game_type: GameType, outcome: str, local: str, visitante: str) -> str:
    if outcome == "L":
        return local
    if outcome == "V":
        return visitante
    return format_outcome(game_type, outcome)


def _risk_label(risk: float) -> str:
    if risk >= 0.55:
        return "Alto"
    if risk >= 0.42:
        return "Medio"
    return "Bajo"


def _localia_factor(game_type: GameType, top_outcome: str, local: str) -> str:
    if top_outcome == "L":
        return f"La localia favorece a {local} dentro del modelo."
    if top_outcome == "V":
        return "El visitante supera la ventaja habitual de localia en la estimacion."
    if game_type == GameType.PROTOUCH:
        return "La localia no alcanza para separar claramente el margen del partido."
    return "La localia no domina; el empate permanece competitivo."


def _generic_form_factor(gap: float) -> str:
    if gap >= 0.18:
        return "La lectura agregada del modelo sugiere ventaja reciente clara para la opcion principal."
    if gap >= 0.08:
        return "La forma estimada da ventaja ligera, sin eliminar riesgo de sorpresa."
    return "La forma reciente estimada no separa con fuerza a las opciones."


def _differential_factor(top_probability: float, second_probability: float) -> str:
    gap = top_probability - second_probability
    if gap >= 0.18:
        return "El diferencial ofensivo/defensivo implícito favorece de forma clara al favorito."
    if gap >= 0.08:
        return "El diferencial estimado favorece al favorito, pero con margen moderado."
    return "El diferencial estimado es estrecho; conviene evaluar cobertura."


def _head_to_head_factor() -> str:
    return "No se cargo historial directo entre equipos; este factor queda neutral hasta tener datos."


def _market_factor(has_market: bool, top_probability: float, gap: float) -> str:
    if not has_market:
        return "No se cargaron momios/probabilidades de mercado; la lectura usa modelos internos."
    if top_probability >= 0.50 and gap >= 0.15:
        return "El mercado respalda al favorito con ventaja consistente."
    if gap <= 0.08:
        return "El mercado muestra partido parejo; la cobertura gana valor."
    return "El mercado aporta ventaja, pero no suficientemente amplia para ignorar riesgo."


def _volatility_factor(volatility: float, gap: float, third_probability: float) -> str:
    if volatility >= 0.96 and gap <= 0.06:
        return "Volatilidad muy alta: las tres opciones estan cerca."
    if volatility >= 0.90 or gap <= 0.12:
        return "Volatilidad media-alta: la segunda opcion merece atencion."
    if third_probability >= 0.25:
        return "Volatilidad moderada: la tercera opcion aun tiene presencia no trivial."
    return "Volatilidad baja: el favorito concentra suficiente probabilidad."


def _natural_message(
    game_type: GameType,
    local: str,
    visitante: str,
    favorite: str,
    coverage_type: str,
    top_probability: float,
    second_probability: float,
    gap: float,
    volatility: float,
) -> str:
    middle_name = "Diferencia" if game_type == GameType.PROTOUCH else "Empate"
    if coverage_type == "Fijo":
        return (
            f"{local} vs {visitante}: se recomienda dejar fijo a {favorite} porque concentra "
            f"{top_probability:.0%} de probabilidad estimada y la ventaja sobre la segunda opcion "
            f"es de {gap:.1%}. El costo adicional de cobertura no parece prioritario."
        )
    if coverage_type == "Doble":
        return (
            f"{local} vs {visitante}: se recomienda cubrir con doble porque, aunque {favorite} "
            f"tiene ligera ventaja, la segunda opcion alcanza {second_probability:.0%} y justifica "
            f"el costo adicional. En este tipo de partido, {middle_name} puede ser una cobertura clave."
        )
    return (
        f"{local} vs {visitante}: se recomienda triple porque la volatilidad es muy alta "
        f"({volatility:.0%}) y ninguna opcion se separa lo suficiente. Es un partido de alto impacto "
        "para proteger la quiniela si el presupuesto lo permite."
    )
