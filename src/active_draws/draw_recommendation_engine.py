"""Home recommendation engine for active draws."""

from __future__ import annotations

from src.recommendations.recommendation_explainer import explain_recommendation
from src.recommendations.recommendation_rules import classify_recommendation
from src.recommendations.recommendation_score import calculate_recommendation_score


def generate_home_recommendation(draw: dict) -> dict:
    """Generate Home recommendation output for one draw."""

    score = calculate_recommendation_score(draw)
    recommendation, action, risk, button = classify_recommendation(draw, score)
    return {
        "game_name": draw.get("game_name", "Dato no disponible"),
        "recommendation": recommendation,
        "recommendation_score": score,
        "recommended_action": action,
        "reason": explain_recommendation(draw, score),
        "risk_level": risk,
        "data_quality_score": int(draw.get("data_quality_score", 0)),
        "next_step_button": button,
    }

